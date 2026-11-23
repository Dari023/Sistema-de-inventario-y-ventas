document.addEventListener('DOMContentLoaded', function () {
    const enlace = document.getElementById('enlace-cliente');
    const boton = document.getElementById('copiar-enlace-cliente');
    const aviso = document.getElementById('aviso-enlace-cliente');

    if (!enlace || !boton || !aviso) return;

    boton.addEventListener('click', async function () {
        try {
            if (!navigator.clipboard?.writeText) {
                throw new Error('Portapapeles no Disponible');
            }

            await navigator.clipboard.writeText(enlace.value);
            aviso.textContent = 'Enlace Copiado';
        } catch {
            enlace.focus();
            enlace.select();
        }
    });
});