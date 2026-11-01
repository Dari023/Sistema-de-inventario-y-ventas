import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/Api";

export const CompraDetail = () => {
  const { id_compra } = useParams();
  const [compra, setCompra] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .get(`compras/${id_compra}/`)
      .then(({ data }) => setCompra(data))
      .catch((err) =>
        setError(err.response?.data?.error || "Compra no encontrada")
      );
  }, [id_compra]);

  if (error) {
    return (
      <div>
        <h2>Error</h2>
        <p>{error}</p>
        <Link to="/">Volver al inicio</Link>
      </div>
    );
  }

  if (!compra) return <p>Cargando...</p>;

  const tieneEnvio = compra.nombre_invitado || compra.direccion_invitado;

  return (
    <div>
      <h2>Compra confirmada</h2>
      <p>Número de compra: {compra.id_compra}</p>
      <p>Fecha: {new Date(compra.fecha_pedido).toLocaleString()}</p>

      <h3>Productos</h3>
      <ul>
        {compra.detalles.map((d) => (
          <li key={d.id}>
            {d.cantidad} × {d.producto_nombre} — ${d.subtotal}
          </li>
        ))}
      </ul>
      <h3>Total: ${compra.total}</h3>

      {tieneEnvio && (
        <section>
          <h3>Datos de envío</h3>
          {compra.nombre_invitado && <p>{compra.nombre_invitado}</p>}
          {compra.rut_invitado && <p>RUT: {compra.rut_invitado}</p>}
          {compra.email_invitado && <p>Email: {compra.email_invitado}</p>}
          {compra.telefono_invitado && <p>Teléfono: {compra.telefono_invitado}</p>}
          {compra.direccion_invitado && <p>Dirección: {compra.direccion_invitado}</p>}
        </section>
      )}

      <Link to="/">Volver al inicio</Link>
    </div>
  );
};