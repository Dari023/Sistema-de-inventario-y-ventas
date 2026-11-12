import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/Api";
import "../styles/CompraDetail.css";

const formatoMonto = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
  maximumFractionDigits: 0,
});

export const CompraDetail = () => {
  const { id_compra } = useParams();
  const [compra, setCompra] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setCompra(null);
    setError(null);

    api
      .get(`compras/${id_compra}/`)
      .then(({ data }) => setCompra(data))
      .catch((err) =>
        setError(
          err.response?.data?.error ||
          'No Pudimos Cargar el Comprobante de tu Compra'
        )
      );
  }, [id_compra]);

  if (error) {
    return (
      <section className='comprobante py-4'>
        <h1 className='comprobante-titulo'>Compra no Disponible</h1>
        <p role='alert'>{error}</p>
        <Link to='/'>Volver al Inicio</Link>
      </section>
    );
  }

  if (!compra) {
    return (
      <p className='text-center py-5' role='status'>Cargando tu Comprobante</p>
    );
  }

  const tieneDatos =
    compra.nombre_invitado ||
    compra.rut_invitado ||
    compra.email_invitado ||
    compra.telefono_invitado ||
    compra.direccion_invitado;

  const fecha = new Date(compra.fecha_pedido).toLocaleString("es-CL", {
    dateStyle: "long",
    timeStyle: "short",
  });

  return (
    <article className = 'comprobante'>
      <header className = 'comprobante-cabecera'>
        <p className = 'comprobante-sobretitulo'>Amigos del Vuelo</p>

        <h1 className = 'comprobante-titulo'>
          COMPRA CONFIRMADA
        </h1>

        <p className = 'comprobante-texto mb-0'>
          Gracias por tu compra, te sugerimos conservar este comprobante para identificar tu pedido
        </p>
      </header>

      <dl className = 'comprobante-datos'>
        <div>
          <dt>Número de Compra</dt>
          <dd className = 'comprobante-numero'>
            {compra.id_compra}
          </dd>
        </div>

        <div>
          <dt>Fecha de Compra</dt>
          <dd>{fecha}</dd>
        </div>
      </dl>

      <section className = 'productos-comprados'>
        <h2 id = 'productos-comprados' className = 'comprobante-subtitulo'>
          Resumen de tu Compra
        </h2>

        <ul className = 'comprobante-productos'>
          {compra.detalles.map((detalle) => (
            <li key = {detalle.id} className = 'comprobante-producto'>
              <div>
                <p className = 'comprobante-producto-nombre'>
                  {detalle.producto_nombre}
                </p>
                <p className = 'comprobante-texto small mb-0'>
                  Cantidad: {detalle.cantidad}
                </p>
              </div>

              <span className = 'comprobante-subtotal'>
                {formatoMonto.format(Number(detalle.subtotal))}
              </span>
            </li>
          ))}
        </ul>

        <div className = 'comprobante-total'>
          <span>Total Pagado</span>
          <strong>
            {formatoMonto.format(Number(compra.total))}
          </strong>
        </div>
      </section>

      {tieneDatos && (
        <section className = 'comprobante-comprador'>
          <h2 id = 'datos-compra' className = 'comprobante-subtitulo'>
            Datos Compra
          </h2>

          <dl className = 'comprobante-datos mb-0'>
            {compra.nombre_invitado && (
              <div>
                <dt>Nombre</dt>
                <dd>{compra.nombre_invitado}</dd>
              </div>
            )}

            {compra.rut_invitado && (
              <div>
                <dt>RUT</dt>
                <dd>{compra.rut_invitado}</dd>
              </div>
            )}

            {compra.email_invitado && (
              <div>
                <dt>Correo Electrónico</dt>
                <dd>{compra.email_invitado}</dd>
              </div>
            )}

            {compra.telefono_invitado && (
              <div>
                <dt>Teléfono de Contacto</dt>
                <dd>{compra.telefono_invitado}</dd>
              </div>
            )}

            {compra.direccion_invitado && (
              <div className = 'comprobante-direccion'>
                <dt>Dirección de Entrega</dt>
                <dd>{compra.direccion_invitado}</dd>
              </div>
            )}
          </dl>
        </section>
      )}
      <section className="comprobante-comprador">
        <h2 id="datos-entrega" className="comprobante-subtitulo">
          Entrega
        </h2>
        <dl className="comprobante-datos mb-0">
          <div>
            <dt>Tipo</dt>
            <dd>
              {compra.tipo_entrega === "envio"
                ? "Envío a domicilio"
                : "Retiro en tienda"}
            </dd>
          </div>
          {compra.tipo_entrega === "envio" && compra.direccion_invitado && (
            <div>
              <dt>Dirección</dt>
              <dd>{compra.direccion_invitado}</dd>
            </div>
          )}
        </dl>
      </section>

      <footer className = 'comprobante-pie'>

        {compra.token_resenas && (
          <Link to={`/resenas/${encodeURIComponent(compra.token_resenas)}`} className='comprobante-boton'>
            Valorar mis Productos
          </Link>
        )}

        <Link to="/catalogo" className="comprobante-boton">
          Seguir comprando
        </Link>

        <Link to="/" className="comprobante-enlace">
          Volver al inicio
        </Link>
      </footer>
    </article>
  );
};