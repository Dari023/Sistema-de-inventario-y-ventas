import { useState, useEffect } from "react";
import { Routes, Route, Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import { Inicio } from "./modules/Inicio";
import { ProductoListar } from "./modules/ProductoListar";
import { ProductoDetalles } from "./modules/ProductoDetalles";
import { Carrito } from "./modules/Carrito";
import { Login } from "./modules/Login";
import { Registro } from "./modules/Registro";
import { MiCuenta } from "./modules/MiCuenta";
import { Checkout } from "./modules/Checkout";
import { CompraDetail } from "./modules/CompraDetail";
import { ToastContainer } from 'react-toastify';
import { Resenas } from "./modules/Resenas";
import 'react-toastify/dist/ReactToastify.css';
import Logo from "./assets/Logo.jpeg";
import "bootstrap-icons/font/bootstrap-icons.css";
import { Contacto } from "./modules/Contacto";

export const App = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    setIsAuthenticated(!!token);
  }, [location]);

  const cerrarSesion = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setIsAuthenticated(false);
    navigate("/login");
  };

  const numeroWhatsApp  = "56968571198";
  const correoContacto = "apatadiego1@gmail.com";
  const enlaceWhatsApp = `https://wa.me/${numeroWhatsApp}?text=${encodeURIComponent(
  "Hola, quisiera consultar por sus productos artesanales."
)}`;

  const redesSociales = [
    { nombre: "Instagram", icono: "bi-instagram", enlace: "" },
    { nombre: "Facebook", icono: "bi-facebook", enlace: "" },
    { nombre: "WhatsApp", icono: "bi-whatsapp", enlace: enlaceWhatsApp},
];

  return (
    <div className="d-flex flex-column min-vh-100">
      <ToastContainer position="top-right" autoClose={2000} />
      <header className="tienda-cabecera">
        <div className="container py-3">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
            <Link to="/" className="tienda-marca">
              <img
                src={Logo}
                alt="Logo Amigos del Vuelo"
                className="tienda-logo"
              />
              <span>Amigos del Vuelo</span>
            </Link>
            <nav className="nav gap-2 align-items-center">
              <NavLink to="/" end className="nav-link tienda-enlace">Inicio</NavLink>
              <Link to="/catalogo" className="nav-link tienda-enlace">Catálogo</Link>
              <NavLink to="/carrito" className="nav-link tienda-enlace">Mi carrito</NavLink>
              {!isAuthenticated ? (
                <>
                  <Link to="/login" className="nav-link tienda-enlace">Iniciar Sesión</Link>
                  <Link to="/registro" className="nav-link tienda-enlace">Registrarse</Link>
                  
                </>
              ) : (
                <>
                  <NavLink to="/mi-cuenta" className="nav-link tienda-enlace">Mi cuenta</NavLink>
                  <button onClick={cerrarSesion} className="btn btn-outline-danger btn-sm ms-2">Cerrar Sesión</button>
                </>
              )}
            </nav>
          </div>
        </div>
      </header>

      <main className="container py-4 py-md-5 flex-grow-1">
        <Routes>
          <Route path="/" element={<Inicio />} />
          <Route path="/catalogo" element={<ProductoListar />} />
          <Route path="/producto/:id" element={<ProductoDetalles />} />
          <Route path="/carrito" element={<Carrito />} />
          <Route path="/login" element={<Login />} />
          <Route path="/registro" element={<Registro />} />
          <Route path="/mi-cuenta" element={<MiCuenta />} />
          <Route path="/carrito" element={<Carrito />} />
          <Route path="/checkout" element={<Checkout />} />
          <Route path="/compra/:id_compra" element={<CompraDetail />} />
          <Route path='/resenas/:token' element={<Resenas />} />
          <Route path="/contacto" element={<Contacto />} />
        </Routes>
      </main>


      <footer className="tienda-pie tienda-footer">
        <div className="container">
          <div className="tienda-footer-grid">

            <div className="tienda-footer-columna">
              <h2>Amigos del Vuelo</h2>
              <p>
                Artesanías hechas a mano, creadas con
                cariño y dedicación.
              </p>

              <div className="tienda-footer-redes">
                {redesSociales.map((red) =>
                  red.enlace ? (
                    <a
                      key={red.nombre}
                      href={red.enlace}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={red.nombre}
                      title={red.nombre}
                    >
                      <i className={`bi ${red.icono}`}></i>
                    </a>
                  ) : (
                    <span key={red.nombre} title={`${red.nombre}: próximamente`}>
                      <i className={`bi ${red.icono}`}></i>
                    </span>
                  )
                )}
              </div>
            </div>

            <div className="tienda-footer-columna">
              <h2>Información</h2>

              <div className="tienda-footer-enlaces">
                <Link to="/catalogo">Catálogo</Link>
                <span>Preguntas frecuentes</span>
                <span>Envíos y retiros</span>
                <span>Términos y condiciones</span>
              </div>
            </div>

            <div className="tienda-footer-columna">
              <h2>Contacto</h2>

              <div className="tienda-footer-enlaces">
                <Link to="/contacto">
                  <i className="bi bi-chat-dots"></i> Enviar consulta
                </Link>
                {enlaceWhatsApp ? (
                  <a href={enlaceWhatsApp} target="_blank" rel="noopener noreferrer">
                    <i className="bi bi-whatsapp"></i> WhatsApp
                  </a>
                ) : (
                  <span><i className="bi bi-whatsapp"></i> WhatsApp</span>
                )}

                {correoContacto ? (
                  <a href={`mailto:${correoContacto}`}>
                    <i className="bi bi-envelope"></i> Correo electrónico
                  </a>
                ) : (
                  <span><i className="bi bi-envelope"></i> Correo electrónico</span>
                )}

                <span>
                  <i className="bi bi-geo-alt"></i> Arica, Chile
                </span>
              </div>
            </div>

          </div>

          <div className="tienda-footer-inferior">
            <p>
              © {new Date().getFullYear()} Amigos del Vuelo.
              Todos los derechos reservados.
            </p>
          </div>
        </div>
      </footer>

    </div>
  );
};