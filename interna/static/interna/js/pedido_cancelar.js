document.addEventListener('DOMContentLoaded', function () {
    const mostrar = document.getElementById('mostrar-cancelacion');
    const ocultar = document.getElementById('ocultar-cancelacion');
    const formulario = document.getElementById('formulario-cancelacion');
    const motivo = document.getElementById('motivo-cancelacion');

    if (!mostrar || !ocultar || !formulario || !motivo) return;

    mostrar.addEventListener('click', function () {
        formulario.hidden = false;
        motivo.focus();
    });

    ocultar.addEventListener('click', function () {
        formulario.hidden = true;
        mostrar.focus();
    });
});