import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/Api';

const moneda = (valor) =>
  Number(valor).toLocaleString('es-CL', {style: 'currency', currency: 'CLP', maximumFractionDigits: 0});

export const Pedidos = () => {
  const [pedidos, setPedidos] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let activo = true;

    api.get('mi-cuenta/pedidos/')
      .then((response) => {
        if (activo) setPedidos(response.data);
      })
      .catch(() => {
        if (activo) setError(true);
      });

    return () => {
      activo = false;
    };
  }, []);

  return (
    <section>
      <h2 className='h4 mb-3'>Mis Pedidos</h2>

      {error ? (
        <div className='alert alert-danger'>
          No Pudimos Cargar tus Pedidos, Inténtalo Nuevamente
        </div>
      ) : pedidos === null ? (
        <p className='text-muted'>Cargando Pedidos</p>
      ) : pedidos.length === 0 ? (
        <p className='text-muted'>Aún no Tienes Pedidos</p>
      ) : (
        <div className='list-group'>
          {pedidos.map((pedido) => {
            const personalizado = pedido.tipo_pedido === 'personalizado';
            const articulos = personalizado
              ? pedido.detalles_personalizados ?? []
              : pedido.detalles ?? [];

            return (
              <div key={pedido.id} className='list-group-item p-3'>
                <div className='d-flex justify-content-between align-items-start flex-wrap gap-3'>
                  <div>
                    {personalizado ? (
                      <strong>Pedido Personalizado #{pedido.id}</strong>
                    ) : (
                      <Link to={`/compra/${pedido.id_compra}`} className='fw-bold text-dark'>
                        Pedido #{pedido.id}
                      </Link>
                    )}

                    <small className='d-block text-muted mt-1'>
                      {new Date(pedido.fecha_pedido).toLocaleString('es-CL')}
                    </small>

                    <div className='d-flex flex-wrap gap-2 mt-2'>
                      <span
                        className={`badge ${
                          pedido.estado === 'pagado'
                            ? 'text-bg-success'
                            : 'text-bg-warning'
                        }`}
                      >
                        {pedido.estado === 'pagado' ? 'Pagado' : 'Pago pendiente'}
                      </span>

                      {pedido.cancelado && (
                        <span className='badge text-bg-danger'>Cancelado</span>
                      )}
                    </div>
                  </div>

                  <div className='text-end'>
                    <strong>{moneda(pedido.total)}</strong>
                    <small className='d-block text-muted'>
                      {articulos.length} artículo
                      {articulos.length === 1 ? '' : 's'}
                    </small>
                  </div>

                  <div className='d-flex flex-wrap gap-2'>
                    <Link to={`/seguimiento/${pedido.id_compra}`} className='btn btn-sm btn-outline-secondary'>
                      Seguimiento
                    </Link>

                    {!personalizado && (
                      <Link to={`/compra/${pedido.id_compra}`} className='btn btn-sm btn-outline-secondary'>
                        Comprobante
                      </Link>
                    )}

                    {personalizado && pedido.enlace_cliente && (
                    <a href={pedido.enlace_cliente} className='btn btn-sm btn-dark'>
                      {pedido.cancelado || pedido.estado === 'pagado'
                        ? 'Ver encargo'
                        : 'Ver y pagar'}
                    </a>
                  )}
                  </div>
                </div>

                {personalizado && (
                  <details className='border-top pt-3 mt-3'>
                    <summary className='fw-semibold'>
                      Ver Artículos del Encargo
                    </summary>

                    {articulos.map((articulo) => (
                      <div key={articulo.id} className='border-bottom py-3'>
                        <div className='d-flex align-items-start gap-3'>
                          {articulo.imagen_referencia && (
                            <a href={articulo.imagen_referencia} target='_blank' rel='noopener noreferrer'>
                              <img src={articulo.imagen_referencia} alt='Referencia del artículo' className='img-thumbnail' width='100'/>
                            </a>
                          )}

                          <div className='flex-grow-1'>
                            <p className='mb-2 text-break' style={{ whiteSpace: 'pre-line' }}>
                              {articulo.descripcion}
                            </p>

                            <p className='small text-secondary mb-1'>
                              Cantidad: {articulo.cantidad} · Precio unitario:{' '}
                              {moneda(articulo.precio_unitario)}
                            </p>

                            <p className='small text-secondary mb-1'>
                              Fabricadas: {articulo.unidades_fabricadas} de{' '}
                              {articulo.cantidad}
                            </p>

                            <strong>{moneda(articulo.subtotal)}</strong>
                          </div>
                        </div>
                      </div>
                    ))}
                  </details>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};