import { useState, useEffect } from 'react';
import { Link } from "react-router-dom";
import { api } from '../api/Api';
import bannerTienda from "../assets/Portada.png";
import '../styles/FAQ.css';

export const Inicio = () => {
  const [preguntas, setPreguntas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let paginaActiva = true;

    api
      .get('preguntas-frecuentes/')
      .then((response) => {
        if (paginaActiva) {
          setPreguntas(response.data);
        }
      })
      .catch(() => {
        if (paginaActiva) {
          setError('No Pudimos Cargar las Preguntas Frecuentes');
        }
      })
      .finally(() => {
        if (paginaActiva) {
          setCargando(false);
        }
      });

    return () => {
      paginaActiva = false;
    };
  }, []);

  return (
    <section>
      <div className='catalogo-banner mb-4 mb-md-5'>
        <img src={bannerTienda} className="catalogo-banner-imagen"/>
      </div>

      <div className="text-center mx-auto mb-5">
        <p className="text-secondary mb-4">
          Descubre nuestros productos hechos a mano y encuentra tu próximo favorito
        </p>

        <Link to='/catalogo' className="btn boton-principal px-4 py-3">
          Explorar Catálogo
        </Link>
      </div>

      <section className='faq-inicio'>
        <div className='faq-inicio-cabecera'>
          <h2>PREGUNTAS FRECUENTES</h2>
          <p>Resuelve tus Dudas Antes de Comprar</p>
        </div>

        {cargando && <p>Cargando Preguntas Frecuentes</p>}

        {error && <p>{error}</p>}

        {!cargando && !error && preguntas.length === 0 && (
          <p>No hay Preguntas Frecuentes Disponibles</p>
        )}

        <div className='faq-inicio-lista'>
          {preguntas.map((pregunta) => (
            <details key={pregunta.id} className='faq-inicio-item'>
              <summary>{pregunta.pregunta}</summary>

              <p className='faq-inicio-respuesta'>
                {pregunta.respuesta}
              </p>
            </details>
          ))}
        </div>
      </section>
    </section>
  );
};