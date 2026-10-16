import { useState, useEffect } from "react";
import { Routes, Route, Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import { ProductoListar } from "./modules/ProductoListar";
import { ProductoDetalles } from "./modules/ProductoDetalles";
import { Carrito } from "./modules/Carrito";
import { Login } from "./modules/Login";
import { Registro } from "./modules/Registro";
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

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
  return (
    <div className="d-flex flex-column min-vh-100">
      <ToastContainer position="top-right" autoClose={2000} />
      <header className="tienda-cabecera">
        <div className="container py-3">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
            <Link to="/" className="tienda-marca">
              Amigos del Vuelo
            </Link>
            <nav className="nav gap-2 align-items-center">
              <NavLink to="/" end className="nav-link tienda-enlace">Productos</NavLink>
              <NavLink to="/carrito" className="nav-link tienda-enlace">Mi carrito</NavLink>
              {!isAuthenticated ? (
                <>
                  <Link to="/login" className="nav-link tienda-enlace">Iniciar Sesión</Link>
                  <Link to="/registro" className="nav-link tienda-enlace">Registrarse</Link>
                </>
              ) : (
                <button onClick={cerrarSesion} className="btn btn-outline-danger btn-sm ms-2">Cerrar Sesión</button>
              )}
            </nav>
          </div>
        </div>
      </header>

      <main className="container py-4 py-md-5 flex-grow-1">
        <Routes>
          <Route path="/" element={<ProductoListar />} />
          <Route path="/producto/:id" element={<ProductoDetalles />} />
          <Route path="/carrito" element={<Carrito />} />
          <Route path="/login" element={<Login />} />
          <Route path="/registro" element={<Registro />} />
        </Routes>
      </main>

      <footer className="tienda-pie py-3">
        <div className="container text-center">
          Amigos del Vuelo
        </div>
      </footer>
    </div>
  );
};