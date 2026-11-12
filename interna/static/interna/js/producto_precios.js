document.addEventListener('DOMContentLoaded', function () {
    const panel = document.getElementById('precio-sugerido');
    const precio = document.getElementById('id_precio');
    const tiempo = document.getElementById('id_tiempo_fabricacion_minutos');
    if (!panel || !precio || !tiempo) return;

    const formulario = precio.form;
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
        if (!tiempo.value || !tiempo.checkValidity()) {
            mostrarMensaje('Completa el tiempo de trabajo y la receta para calcular la sugerencia.');
            return;
        }
        const csrf = formulario.querySelector("[name='csrfmiddlewaretoken']");
        if (!csrf) {
            mostrarMensaje('Recarga la página para calcular la sugerencia.');
            return;
        }
        const datos = new URLSearchParams();
        const controles = new FormData(formulario);
        controles.forEach(function (valor, nombre) {
            if (typeof valor === 'string' && (
                nombre.startsWith('materiales-') ||
                nombre === 'tiempo_fabricacion_minutos'
            )) datos.append(nombre, valor);
        });
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
        const nombre = evento.target.name || '';
        if (nombre === 'tiempo_fabricacion_minutos' || nombre.startsWith('materiales-')) {
            programarCalculo();
        }
    }
    formulario.addEventListener('input', cambioDeCalculo);
    formulario.addEventListener('change', cambioDeCalculo);
    formulario.addEventListener('materiales-cambiados', programarCalculo);
    window.addEventListener('focus', programarCalculo);
    boton.addEventListener('click', function () {
        if (sugerencia === null) return;
        precio.value = sugerencia;
        precio.dispatchEvent(new Event('input', { bubbles: true }));
        precio.dispatchEvent(new Event('change', { bubbles: true }));
    });
    programarCalculo();
});