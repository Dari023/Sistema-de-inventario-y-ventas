document.addEventListener("DOMContentLoaded", function () {
    const categoria = document.getElementById("id_categoria");
    const bloqueTallas = document.getElementById("bloque-tallas");
    const bloquePrecios = document.getElementById("bloque-precios-tallas");
    const datos = document.getElementById("categorias-con-tallas");

    if (!categoria?.form || !bloqueTallas || !bloquePrecios || !datos) return;

    const categoriasConTallas = JSON.parse(datos.textContent).map(String);
    const hayVariantesGuardadas = JSON.parse(
    document.getElementById("hay-variantes-guardadas").textContent);
    const campos = categoria.form.querySelectorAll('[name^="talla-"]');
    const casillas = categoria.form.querySelectorAll('[name^="talla-"][name$="-ofrecer"]');
    const tallasMarcadas = new Set();

    function actualizarCategoria() {
        const mostrar = hayVariantesGuardadas ||
            categoriasConTallas.includes(categoria.value);

        bloqueTallas.hidden = !mostrar;
        bloquePrecios.hidden = !mostrar;

        if (hayVariantesGuardadas) return;

        casillas.forEach(function (casilla) {
            if (!mostrar && casilla.checked) {
                tallasMarcadas.add(casilla);
                casilla.checked = false;
            } else if (mostrar && tallasMarcadas.delete(casilla)) {
                casilla.checked = true;
            }
        });

        campos.forEach(function (campo) {
            campo.disabled = !mostrar;
        });

        casillas[0]?.dispatchEvent(new Event("change", { bubbles: true }));
    }

    categoria.addEventListener("change", actualizarCategoria);
    actualizarCategoria();
});