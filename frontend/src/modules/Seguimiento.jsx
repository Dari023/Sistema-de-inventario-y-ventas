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
      .catch(() => setError("No Pudimos Cargar el Seguimiento de Este Pedido"));
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

  if (!compra) return <p className="container py-4">Cargando Seguimiento</p>;

  const esRetiro = compra.tipo_entrega === "retiro";

  const flujos = {
    normal: {
      retiro: ['disponible_retiro', 'entregado'],
      envio: ['enviado', 'entregado']
    },
    personalizado: {
      retiro: ['en_confeccion', 'disponible_retiro', 'entregado'],
      envio: ['en_confeccion', 'listo', 'enviado', 'entregado'],
    }
  };

  const etiquetas = {
    en_confeccion: 'En Confección',
    listo: 'Listo',
    disponible_retiro: 'Disponible Para Retiro',
    enviado: 'Enviado',
    entregado: esRetiro ? 'Retirado' : 'Entregado'
  };

  const flujo = flujos[compra.tipo_pedido]?.[compra.tipo_entrega] ?? [];

  const etapas = flujo.map((id) => ({id, label: etiquetas[id]}));

  const etapaActual = flujo.indexOf(compra.etapa);

  return (
    <section className="container py-4">
      <h2 className="mb-4">Seguimiento del Pedido</h2>
      <div className="bg-light p-3 rounded mb-4">
        <p className="mb-1"><strong>Número de Compra:</strong> {compra.id_compra}</p>
        <p className="mb-0">
          <strong>Tipo de Entrega:</strong> {esRetiro ? "Retiro en tienda" : "Envío a domicilio"}
        </p>
        <p className='mb-0 mt-2'>
          <strong>Estado del Pago:</strong>{' '}
          {compra.estado === 'pagado' ? 'Pagado' : 'Pendiente'}
        </p>
      </div>
        {compra.cancelado ? (
          <div className='alert alert-danger'>
            Este Pedido Está Cancelado, no Continuará su Preparación ni Entrega
          </div>
        ) : etapas.length === 0 ? (
          <div className='alert alert-warning'>
            No Pudimos Determinar las Etapas de Este Pedido
          </div>
        ) : (
          <div className='d-flex flex-column gap-4 mt-4'>
            {etapas.map((etapa, index) => {
              const completado = index <= etapaActual;

              return (
                <div
                  key={etapa.id}
                  className={`d-flex align-items-center gap-3 ${
                    completado ? '' : 'opacity-50'
                  }`}
                >
                  <div
                    className={`rounded-circle d-flex justify-content-center
                      align-items-center text-white fw-bold ${
                        completado ? 'bg-success' : 'bg-secondary'
                      }`}
                    style={{ width: '35px', height: '35px', flexShrink: 0 }}
                  >
                    {completado ? '✓' : index + 1}
                  </div>
                  <strong className='fs-5'>{etapa.label}</strong>
                </div>
              );
            })}
          </div>
        )}
      <div className="mt-5">
        <Link to="/mi-cuenta" className="btn btn-secondary">Volver</Link>
      </div>
    </section>
  );
};