document.addEventListener('DOMContentLoaded', function () {
    const panel = document.getElementById('precio-sugerido');
    const precio = document.getElementById('id_precio');
    const tiempo = document.getElementById('id_tiempo_fabricacion_minutos');
    if (!panel || !precio || !tiempo) return;

    const formulario = precio.form;
    const selectorTalla = document.getElementById("calcular-talla");

    function sincronizarTallas() {
        let primeraTalla = "";

        for (const opcion of selectorTalla.options) {
            if (!opcion.value) continue;

            const ofrecer = formulario.elements.namedItem(
                `talla-${opcion.value}-ofrecer`
            );
            const marcada = Boolean(ofrecer?.checked);

            opcion.hidden = !marcada;
            opcion.disabled = !marcada;

            if (marcada && !primeraTalla) {
                primeraTalla = opcion.value;
            }
        }

        const tieneTallas = primeraTalla !== "";
        const opcionGeneral = selectorTalla.querySelector('option[value=""]');

        opcionGeneral.hidden = tieneTallas;
        opcionGeneral.disabled = tieneTallas;

        if (!tieneTallas) {
            selectorTalla.value = "";
        } else if (
            !selectorTalla.value ||
            selectorTalla.selectedOptions[0]?.disabled
        ) {
            selectorTalla.value = primeraTalla;
        }

        document.getElementById("bloque-tiempo-general").hidden = tieneTallas;
        tiempo.disabled = tieneTallas;
        tiempo.required = !tieneTallas;
        document.getElementById("bloque-precio-base").hidden = tieneTallas;
        precio.disabled = tieneTallas;
        precio.required = !tieneTallas;
    }

    function prepararReceta(talla, campoTiempo) {
        const datos = new URLSearchParams();
        datos.set("tiempo_fabricacion_minutos", campoTiempo.value);

        const campoCantidad = talla
            ? `cantidad_${talla.toLowerCase()}`
            : "cantidad_requerida";

        let cantidadFilas = 0;

        formulario.querySelectorAll("#lista-materiales .fila-material").forEach(function (fila) {
            if (fila.hidden || fila.querySelector('[name$="-DELETE"]')?.checked) return;

            const materia = fila.querySelector('[name$="-materia_prima"]');
            const cantidad = fila.querySelector(`[name$="-${campoCantidad}"]`);

            if (!materia?.value && !cantidad?.value) return;
            if (talla && materia?.value && !cantidad?.value) return;

            const prefijo = `materiales-${cantidadFilas}`;
            datos.set(`${prefijo}-materia_prima`, materia?.value || "");
            datos.set(`${prefijo}-cantidad_requerida`, cantidad?.value || "");
            cantidadFilas += 1;
        });

        datos.set("materiales-TOTAL_FORMS", String(cantidadFilas));
        datos.set("materiales-INITIAL_FORMS", "0");
        return datos;
    }

    const mensaje = panel.querySelector('[data-mensaje-precio]');
    const resultado = panel.querySelector('[data-resultado-precio]');
    const boton = panel.querySelector('[data-usar-precio]');
    const moneda = new Intl.NumberFormat('es-CL', {
        style: 'currency', currency: 'CLP', maximumFractionDigits: 0,
    });
    let temporizador;
    let solicitud;
    let revision = 0;
    let sugerencia = null;

    function mostrarMensaje(texto) {
        mensaje.textContent = texto;
        resultado.hidden = true;
        boton.disabled = true;
        sugerencia = null;
    }

    function programarCalculo() {
        revision += 1;
        clearTimeout(temporizador);
        if (solicitud) solicitud.abort();
        mostrarMensaje('Actualizando sugerencia…');
        const version = revision;
        temporizador = setTimeout(function () { calcular(version); }, 300);
    }

    async function calcular(version) {
    const talla = selectorTalla.value;
    const campoTiempo = talla
        ? formulario.elements.namedItem(`talla-${talla}-tiempo_minutos`)
        : tiempo;

    if (!campoTiempo?.value || !campoTiempo.checkValidity()) {
        mostrarMensaje("Completa los minutos de confección y la receta seleccionada.");
        return;
    }

    const csrf = formulario.querySelector('[name="csrfmiddlewaretoken"]');
    if (!csrf) {
        mostrarMensaje("Recarga la página para calcular la sugerencia.");
        return;
    }

    const datos = prepararReceta(talla, campoTiempo);
        solicitud = new AbortController();
        panel.setAttribute('aria-busy', 'true');
        try {
            const respuesta = await fetch(panel.dataset.url, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrf.value },
                credentials: 'same-origin',
                body: datos,
                signal: solicitud.signal,
            });
            if (version !== revision) return;
            if (respuesta.redirected) {
                mostrarMensaje('Vuelve a iniciar sesión para calcular la sugerencia.');
                return;
            }
            if (!(respuesta.headers.get('content-type') || '').includes('application/json')) {
                throw new Error('No se pudo calcular. Revisa tu sesión y tus permisos.');
            }
            const datosPrecio = await respuesta.json();
            if (version !== revision) return;
            if (!respuesta.ok) throw new Error(datosPrecio.error || 'Revisa el tiempo y la receta.');

            panel.querySelectorAll('[data-importe]').forEach(function (elemento) {
                elemento.textContent = moneda.format(Number(datosPrecio[elemento.dataset.importe]));
            });
            panel.querySelector('[data-margen]').textContent = Number(datosPrecio.margen).toLocaleString('es-CL');
            panel.querySelector('[data-iva]').textContent = Number(datosPrecio.iva).toLocaleString('es-CL');
            sugerencia = datosPrecio.precio_sugerido;
            mensaje.textContent = 'Sugerencia por unidad, con IVA. El precio final lo eliges tú.';
            resultado.hidden = false;
            boton.disabled = false;
        } catch (error) {
            if (error.name !== 'AbortError' && version === revision) mostrarMensaje(error.message);
        } finally {
            if (version === revision) panel.setAttribute('aria-busy', 'false');
        }
    }

        function cambioDeCalculo(evento) {
        const nombre = evento.target.name || "";
        const cambioOferta = /^talla-[SML]-ofrecer$/.test(nombre);
        const cambioMinutos = /^talla-[SML]-tiempo_minutos$/.test(nombre);

        if (cambioOferta) {
            sincronizarTallas();
        }

        if (
            nombre === "tiempo_fabricacion_minutos" ||
            nombre.startsWith("materiales-") ||
            cambioOferta ||
            cambioMinutos
        ) {
            programarCalculo();
        }
    }

    formulario.addEventListener("input", cambioDeCalculo);
    formulario.addEventListener("change", cambioDeCalculo);
    formulario.addEventListener("materiales-cambiados", programarCalculo);
    window.addEventListener("focus", programarCalculo);
    selectorTalla.addEventListener("change", programarCalculo);

    boton.addEventListener("click", function () {
        if (sugerencia === null) return;

        const talla = selectorTalla.value;
        const destino = talla
            ? formulario.elements.namedItem(`talla-${talla}-precio`)
            : precio;

        if (!destino) return;

        destino.value = sugerencia;
        destino.dispatchEvent(new Event("input", { bubbles: true }));
        destino.dispatchEvent(new Event("change", { bubbles: true }));
    });

    sincronizarTallas();
    programarCalculo();
});