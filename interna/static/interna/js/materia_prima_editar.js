document.addEventListener("DOMContentLoaded", function () {
    const cantidad = document.getElementById("id_cantidad_actual");
    const observacion = document.getElementById("id_observacion");
    const contenedor = document.querySelector(
        '[data-campo="observacion"]'
    );

    if (!cantidad || !observacion || !contenedor) {
        return;
    }

    const cantidadInicial = Number(
        cantidad.dataset.cantidadInicial
    );

    function actualizarObservacion() {
        const cantidadNueva = cantidad.valueAsNumber;
        const cambio =
            Number.isFinite(cantidadNueva) &&
            cantidadNueva !== cantidadInicial;

        contenedor.hidden = !cambio;
        observacion.required = cambio;
    }

    cantidad.addEventListener("input", actualizarObservacion);
    actualizarObservacion();
});