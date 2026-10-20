import { Link } from "react-router-dom";
import bannerTienda from "../assets/Portada.png";

export const Inicio = () => {
  return (
    <section>
      <div className="catalogo-banner mb-4 mb-md-5">
        <img
          src={bannerTienda}
          alt="Conejos tejidos, muñeco Freddie y llaveros de cactus"
          className="catalogo-banner-imagen"
        />
      </div>

      <div className="text-center mx-auto mb-5">
        <p className="text-secondary mb-4">
          Descubre nuestros productos hechos a mano
          y encuentra tu próximo favorito.
        </p>

        <Link to="/catalogo" className="btn boton-principal px-4 py-3">Explorar catálogo</Link>
      </div>
    </section>
  );
};