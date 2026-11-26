document.addEventListener('DOMContentLoaded', function () {
    const boton = document.getElementById('agregar-material');
    const lista = document.getElementById('lista-materiales');
    const plantilla = document.getElementById('material-vacio');
    const total = document.getElementById('id_materiales-TOTAL_FORMS');

    if (!boton || !lista || !plantilla || !total) return;

    boton.addEventListener('click', function () {
        const indice = Number(total.value);
        const contenido = plantilla.innerHTML.replace(
            /__prefix__/g,
            String(indice)
        );

        lista.insertAdjacentHTML('beforeend', contenido);
        total.value = indice + 1;
    });
});