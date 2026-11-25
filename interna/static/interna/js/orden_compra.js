document.addEventListener('DOMContentLoaded', function () {
    const boton = document.getElementById('agregar-material');
    const total = document.getElementById('id_detalles-TOTAL_FORMS');
    const maximo = document.getElementById('id_detalles-MAX_NUM_FORMS');
    const filas = document.getElementById('filas-compra');
    const plantilla = document.getElementById('fila-compra-vacia');

    if (!boton || !total || !maximo || !filas || !plantilla) return;

    function actualizarBoton() {
        boton.disabled = Number(total.value) >= Number(maximo.value);
    }

    boton.addEventListener('click', function () {
        const indice = Number(total.value);

        if (indice >= Number(maximo.value)) return;

        filas.insertAdjacentHTML(
            'beforeend',
            plantilla.innerHTML.replaceAll('__prefix__', indice)
        );

        total.value = indice + 1;
        actualizarBoton();
    });

    actualizarBoton();
});