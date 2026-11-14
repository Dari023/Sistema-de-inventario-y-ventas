document.addEventListener('DOMContentLoaded', function () {
    const lista = document.getElementById('lista-materiales');
    if (!lista) return;

    const plantilla = document.getElementById('material-vacio');
    const total = document.getElementById('id_materiales-TOTAL_FORMS');
    const botonAgregar = document.getElementById('agregar-material');

    function notificarCambio() {
        lista.dispatchEvent(
            new Event('materiales-cambiados', { bubbles: true })
        );
    }

    function actualizarCantidadesPorTalla() {
        const formulario = lista.closest('form');

        for (const talla of ['S','M', 'L']) {
            const ofrecer = formulario.elements.namedItem(`talla-${talla}-ofrecer`);
            const sufijo = `-cantidad_${talla.toLowerCase()}`;

            lista.querySelectorAll(`input[name$="${sufijo}"]`).forEach(function (campo) {
                const fila = campo.closest(".fila-material");
                const campoConEtiqueta = campo.closest("p");
                const visible = Boolean(ofrecer?.checked) && !fila?.hidden;

                campo.disabled = !visible;
                if (campoConEtiqueta) campoConEtiqueta.hidden = !visible;
            });
        }
        const tieneTallas = ["S", "M", "L"].some(function (talla) {
        return formulario.elements.namedItem(`talla-${talla}-ofrecer`)?.checked;
    });

    lista.querySelectorAll('input[name$="-cantidad_requerida"]').forEach(function (campo) {
        const fila = campo.closest(".fila-material");
        const ocultar = tieneTallas || Boolean(fila?.hidden);

        campo.disabled = ocultar;

        const parrafo = campo.closest("p");
        if (parrafo) parrafo.hidden = ocultar;
    });
    }

    function ocultarFila(fila) {
        fila.hidden = true;

        fila.querySelectorAll("select, input[type='number']")
            .forEach(function (campo) {
                campo.disabled = true;

                if (campo.tomselect) {
                    campo.tomselect.disable();
                }
            });
    }

    function prepararFilas(contenedor) {
        contenedor.querySelectorAll('.fila-material')
            .forEach(function (fila) {
                const casilla = fila.querySelector(
                    "input[name$='-DELETE']"
                );

                if (!casilla) return;

                const parrafo = casilla.closest('p');

                if (parrafo) {
                    parrafo.hidden = true;
                }

                if (casilla.checked) {
                    ocultarFila(fila);
                    return;
                }

                const selector = fila.querySelector('.selector-materia');

                if (
                    selector &&
                    !selector.tomselect &&
                    window.TomSelect
                ) {
                    new TomSelect(selector, { create: false });
                }

                const botonQuitar = document.createElement('button');
                botonQuitar.type = 'button';
                botonQuitar.textContent = 'Quitar material';
                botonQuitar.className =
                    'formulario-boton formulario-boton-secundario';

                botonQuitar.addEventListener('click', function () {
                    casilla.checked = true;
                    ocultarFila(fila);
                    notificarCambio();
                });

                fila.appendChild(botonQuitar);
            });
    }

    prepararFilas(lista);

    actualizarCantidadesPorTalla();
    lista.closest('form').addEventListener('change', function (evento) {
        if (/^talla-[SML]-ofrecer$/.test(evento.target.name)) {
            actualizarCantidadesPorTalla();
            notificarCambio();
        }
    });

    if (!plantilla || !total || !botonAgregar) return;

    botonAgregar.addEventListener('click', function () {
        const nuevaFila = document.createElement('div');

        nuevaFila.innerHTML = plantilla.innerHTML.replaceAll(
            '__prefix__',
            total.value
        );

        lista.appendChild(nuevaFila);
        total.value = Number(total.value) + 1;

        prepararFilas(nuevaFila);
        actualizarCantidadesPorTalla();
        notificarCambio();
    });
});