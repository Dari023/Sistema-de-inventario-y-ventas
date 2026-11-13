import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/Api";

export const Seguimiento = () => {
  const { id_compra } = useParams();
  const [compra, setCompra] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get(`compras/${id_compra}/`)
      .then((res) => setCompra(res.data))
      .catch(() => setError("No pudimos cargar el seguimiento de este pedido."));
  }, [id_compra]);

  if (error) {
    return (
      <section className="container py-4">
        <h2>Pedido no disponible</h2>
        <div className="alert alert-danger">{error}</div>
        <Link to="/" className="btn btn-primary">Volver al inicio</Link>
      </section>
    );
  }

  if (!compra) return <p className="container py-4">Cargando seguimiento...</p>;

  const esRetiro = compra.tipo_entrega === "retiro";

  const etapas = [
    { id: "pagado", label: "Pagado" },
    { id: "en_confeccion", label: "En confección" },
    { id: "listo", label: "Listo" },
    {
      id: esRetiro ? "disponible_retiro" : "enviado",
      label: esRetiro ? "Disponible para retiro" : "Enviado",
    },
    { id: "entregado", label: "Entregado" },
  ];

  const indice = etapas.findIndex((e) => e.id === compra.etapa);
  const etapaActual = indice === -1 ? 0 : indice;

  return (
    <section className="container py-4">
      <h2 className="mb-4">Seguimiento del Pedido</h2>
      <div className="bg-light p-3 rounded mb-4">
        <p className="mb-1"><strong>Número de Compra:</strong> {compra.id_compra}</p>
        <p className="mb-0">
          <strong>Tipo de Entrega:</strong> {esRetiro ? "Retiro en tienda" : "Envío a domicilio"}
        </p>
      </div>
      <div className="d-flex flex-column gap-4 mt-4">
        {etapas.map((etapa, index) => {
          const completado = index <= etapaActual;
          return (
            <div key={etapa.id} className={`d-flex align-items-center gap-3 ${completado ? "" : "opacity-50"}`}>
              <div className={`rounded-circle d-flex justify-content-center align-items-center text-white fw-bold ${completado ? "bg-success" : "bg-secondary"}`} style={{ width: "35px", height: "35px", flexShrink: 0 }}>
                {completado ? "✓" : index + 1}
              </div>
              <strong className="fs-5">{etapa.label}</strong>
            </div>
          );
        })}
      </div>
      <div className="mt-5">
        <Link to="/mi-cuenta" className="btn btn-secondary">Volver</Link>
      </div>
    </section>
  );
};