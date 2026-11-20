document.addEventListener('DOMContentLoaded', function () {
    const botonArticulo = document.getElementById(
        'agregar-articulo-personalizado'
    );
    const listaArticulos = document.getElementById(
        'articulos-personalizados'
    );
    const plantillaArticulo = document.getElementById(
        'articulo-personalizado-vacio'
    );
    const totalArticulos = document.getElementById(
        'id_articulos-TOTAL_FORMS'
    );

    if (
        !botonArticulo ||
        !listaArticulos ||
        !plantillaArticulo ||
        !totalArticulos
    ) {
        return;
    }

    botonArticulo.addEventListener('click', function () {
        const indice = Number(totalArticulos.value);

        const contenido = plantillaArticulo.innerHTML.replaceAll(
            'articulos-__prefix__',
            `articulos-${indice}`
        );

        listaArticulos.insertAdjacentHTML('beforeend', contenido);
        totalArticulos.value = indice + 1;
    });

    listaArticulos.addEventListener('click', function (evento) {
        const botonMaterial = evento.target.closest(
            'button[data-agregar-material]'
        );

        if (!botonMaterial) return;

        const articulo = botonMaterial.closest('[data-articulo]');
        const prefijo = botonMaterial.dataset.prefijo;

        const listaMateriales = articulo.querySelector(
            '[data-lista-materiales]'
        );
        const plantillaMaterial = articulo.querySelector(
            'template[data-plantilla-material]'
        );
        const totalMateriales = document.getElementById(
            `id_${prefijo}-TOTAL_FORMS`
        );

        if (!listaMateriales || !plantillaMaterial || !totalMateriales) {
            return;
        }

        const indice = Number(totalMateriales.value);

        const contenido = plantillaMaterial.innerHTML.replaceAll(
            `${prefijo}-__prefix__`,
            `${prefijo}-${indice}`
        );

        listaMateriales.insertAdjacentHTML('beforeend', contenido);
        totalMateriales.value = indice + 1;
    });
});