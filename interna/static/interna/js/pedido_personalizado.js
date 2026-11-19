document.addEventListener('DOMContentLoaded', function () {
    const boton = document.getElementById('agregar-material-personalizado');
    const contenedor = document.getElementById('materiales-personalizados');
    const plantilla = document.getElementById('material-personalizado-vacio');
    const total = document.getElementById('id_materiales-TOTAL_FORMS');

    if (!boton || !contenedor || !plantilla || !total) return;

    boton.addEventListener('click', function () {
        const indice = Number(total.value);
        const contenido = plantilla.innerHTML.replace(
            /__prefix__/g,
            String(indice)
        );

        contenedor.insertAdjacentHTML('beforeend', contenido);
        total.value = indice + 1;
    });
});