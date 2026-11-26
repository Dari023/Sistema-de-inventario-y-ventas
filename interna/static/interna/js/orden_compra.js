document.addEventListener('DOMContentLoaded', function () {
    const boton = document.getElementById('agregar-material');
    const total = document.getElementById('id_detalles-TOTAL_FORMS');
    const maximo = document.getElementById('id_detalles-MAX_NUM_FORMS');
    const filas = document.getElementById('filas-compra');
    const plantilla = document.getElementById('fila-compra-vacia');

    if (!boton || !total || !maximo || !filas || !plantilla) return;

    function actualizarFilas() {
        const lista = filas.querySelectorAll('tr');

        lista.forEach(function (fila, indice) {
            fila.querySelectorAll('[name], [id], [for]').forEach(function (elemento) {
                ['name', 'id', 'for'].forEach(function (atributo) {
                    const valor = elemento.getAttribute(atributo);

                    if (valor) {
                        elemento.setAttribute(
                            atributo,
                            valor.replace(
                                /detalles-\d+-/g,
                                'detalles-' + indice + '-'
                            )
                        );
                    }
                });
            });
        });

        total.value = lista.length;
        boton.disabled = lista.length >= Number(maximo.value);
    }

    boton.addEventListener('click', function () {
        if (Number(total.value) >= Number(maximo.value)) return;

        filas.insertAdjacentHTML(
            'beforeend',
            plantilla.innerHTML.replaceAll('__prefix__', total.value)
        );

        actualizarFilas();
    });

    filas.addEventListener('click', function (evento) {
        const quitar = evento.target.closest('.quitar-material');

        if (!quitar) return;

        quitar.closest('tr').remove();
        actualizarFilas();
    });

    actualizarFilas();
});