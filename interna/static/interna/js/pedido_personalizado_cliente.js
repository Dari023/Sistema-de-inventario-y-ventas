document.addEventListener('DOMContentLoaded', function () {
    const selector = document.getElementById('id_pedido-cliente');
    const buscador = document.getElementById('buscar-cliente');
    const contenedor = document.getElementById('clientes-pedido-datos');

    if (!selector || !contenedor) return;

    const clientes = JSON.parse(contenedor.textContent);

    function normalizar(texto) {
        return texto.normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/[.\s-]/g, '');
    }

    if (buscador) {
        buscador.addEventListener('input', function () {
            const texto = normalizar(buscador.value);

            for (const opcion of selector.options) {
                opcion.hidden = Boolean(
                    opcion.value &&
                    !opcion.selected &&
                    !normalizar(opcion.textContent).includes(texto)
                );
            }
        });
    }

    selector.addEventListener('change', function () {
        const datos = clientes[selector.value];

        if (buscador) {
            buscador.value = '';
            for (const opcion of selector.options) opcion.hidden = false;
        }

        if (!datos) return;

        for (const [nombre, valor] of Object.entries(datos)) {
            const campo = document.getElementById('id_pedido-' + nombre);

            if (campo) {
                campo.value = valor || '';
                campo.dispatchEvent(new Event('input', { bubbles: true }));
                campo.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
    });
});