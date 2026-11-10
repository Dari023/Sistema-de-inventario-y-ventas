import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/Api';
import '../styles/Resenas.css';

function obtenerErrorResena(error) {
  const datos = error.response?.data;

  if (datos?.error) return datos.error;
  if (datos?.detail) return datos.detail;
  if (datos?.non_field_errors) return datos.non_field_errors[0];
  if (datos?.calificacion) return datos.calificacion[0];
  if (datos?.comentario) return datos.comentario[0];
  if (datos?.producto) return datos.producto[0];

  return 'No se Pudo Completar la Operación, Inténtalo Nuevamente';
}

export const Resenas = () => {
  const { token } = useParams();

  const [productos, setProductos] = useState(null);
  const [productoId, setProductoId] = useState('');
  const [calificacion, setCalificacion] = useState(0);
  const [comentario, setComentario] = useState('');
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    let paginaActiva = true;

    setProductos(null);
    setProductoId('');
    setCalificacion(0);
    setComentario('');
    setError('');
    setMensaje('');

    api.get(`resenas/${encodeURIComponent(token)}/`)
      .then((respuesta) => {
        if (!paginaActiva) return;

        const lista = respuesta.data.productos;
        setProductos(lista);

        const primero = lista.find(
          (producto) => producto.resena === null
        );

        if (primero) {
          setProductoId(String(primero.id));
        }
      })
      .catch((error) => {
        if (paginaActiva) {
          setError(obtenerErrorResena(error));
        }
      });

    return () => {
      paginaActiva = false;
    };
  }, [token]);

  const cambiarProducto = (evento) => {
    setProductoId(evento.target.value);
    setCalificacion(0);
    setComentario('');
    setError('');
    setMensaje('');
  };

  const enviarResena = (evento) => {
    evento.preventDefault();

    if (enviando) return;

    setError('');
    setMensaje('');

    if (!productoId || calificacion < 1 || !comentario.trim()) {
      setError('Selecciona un Producto, Califícalo y Escribe tu Comentario');
      return;
    }

    setEnviando(true);

    api.post(`resenas/${encodeURIComponent(token)}/`, {
      producto: Number(productoId),
      calificacion: calificacion,
      comentario: comentario.trim(),
    })
      .then((respuesta) => {
        const lista = productos.map((producto) => {
          if (producto.id === Number(productoId)) {
            return {
              ...producto,
              resena: respuesta.data,
            };
          }

          return producto;
        });

        setProductos(lista);

        const siguiente = lista.find(
          (producto) => producto.resena === null
        );

        setProductoId(siguiente ? String(siguiente.id) : '');
        setCalificacion(0);
        setComentario('');
        setMensaje('Tu Reseña fue Publicada, Gracias por Compartir tu Opinión');
      })
      .catch((error) => {
        setError(obtenerErrorResena(error));
      })
      .finally(() => {
        setEnviando(false);
      });
  };

  if (productos === null) {
    return (
      <main className='resenas'>
        <h1>VALORA TU COMPRA</h1>
        {error ? (<p role='alert'>{error}</p>) : (<p role='status'>Cargando Productos</p>)}
        <Link to='/catalogo'>Volver al Catálogo</Link>
      </main>
    );
  }

  const pendientes = productos.filter(
    (producto) => producto.resena === null
  );

  return (
    <main className='resenas'>
      <h1>VALORA TU COMPRA</h1>
      <p>Puedes dejar una Reseña por cada Producto Comprado</p>

      {mensaje && (
        <p className='resenas-exito' role='status'>{mensaje}</p>
      )}

      {error && (
        <p className='resenas-error' role='alert'>{error}</p>
      )}

      {pendientes.length === 0 ? (
        <p>No Quedan Productos Pendientes de Valorar en esta Compra</p>
      ) : (
        <form className='resenas-tarjeta' onSubmit={enviarResena}>
          <label htmlFor='producto-resena'>
            Producto de tu Compra
          </label>

          <select id='producto-resena' value={productoId} onChange={cambiarProducto} required disabled={enviando}>
            <option value=''>Selecciona un Producto</option>

            {pendientes.map((producto) => (
              <option key={producto.id} value={producto.id}>
                {producto.nombre}
              </option>
            ))}
          </select>

          <fieldset className='resenas-calificacion'>
            <legend>Calificación</legend>

            <div className='resenas-estrellas'>
              {[1, 2, 3, 4, 5].map((numero) => (
                <button key={numero} type='button' disabled={enviando} onClick={() => setCalificacion(numero)}>
                  {numero <= calificacion ? '★' : '☆'}
                </button>
              ))}
            </div>
          </fieldset>

          <label htmlFor='comentario-resena'>Comentario</label>

          <textarea
            id='comentario-resena'
            value={comentario}
            onChange={(evento) => setComentario(evento.target.value)}
            maxLength={500}
            rows={5}
            required
            disabled={enviando}
          />

          <small>{comentario.length}/500 caracteres</small>

          <button className='resenas-enviar' type='submit' disabled={enviando}>
            {enviando ? 'Publicando…' : 'Publicar reseña'}
          </button>
        </form>
      )}

      <Link to='/catalogo'>Volver al Catálogo</Link>
    </main>
  );
};

export const ResenasProducto = ({ productoId }) => {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let paginaActiva = true;

    setDatos(null);
    setError('');

    api.get(`productos/${productoId}/resenas/`)
      .then((respuesta) => {
        if (paginaActiva) {
          setDatos(respuesta.data);
        }
      })
      .catch(() => {
        if (paginaActiva) {
          setError('No Pudimos Cargar las Reseñas');
        }
      });

    return () => {
      paginaActiva = false;
    };
  }, [productoId]);

  return (
    <section className='resenas-publicas'>
      <h2>Valoraciones y Reseñas</h2>

      {error && <p role='alert'>{error}</p>}
      {!datos && !error && (
        <p role='status'>Cargando Reseñas</p>
      )}

      {datos && datos.cantidad === 0 && (
        <p>Este Producto Todavía ha Sido Valorado</p>
      )}

      {datos && datos.cantidad > 0 && (
        <>
          <p>
            <strong>
              {Number(datos.promedio).toLocaleString('es-CL')} / 5
            </strong>
            {' — '}
            {datos.cantidad}{' '}
            {datos.cantidad === 1 ? 'reseña' : 'reseñas'}
          </p>

          {datos.resenas.map((resena) => (
            <article className='resenas-tarjeta' key={resena.id}>
              <p className='resenas-estrellas-texto'>
                {'★'.repeat(resena.calificacion)}
                {'☆'.repeat(5 - resena.calificacion)}
              </p>

              <p className='resenas-comentario'>
                {resena.comentario}
              </p>

              <small>
                Compra verificada ·{' '}
                {new Date(resena.fecha_creacion).toLocaleDateString('es-CL')}
              </small>
            </article>
          ))}
        </>
      )}
    </section>
  );
};