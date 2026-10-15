import { Routes, Route, Link, NavLink } from "react-router-dom";
import { ProductoListar } from "./modules/ProductoListar";
import { ProductoDetalles } from "./modules/ProductoDetalles";
import { Carrito } from "./modules/Carrito";
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

export const App = () => {
  return (
    <div className="d-flex flex-column min-vh-100">
      <ToastContainer position="top-right" autoClose={2000} />
      <header className="tienda-cabecera">
        <div className="container py-3">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
            <Link to="/" className="tienda-marca">
              Amigos del Vuelo
            </Link>
            <nav className="nav gap-2">
              <NavLink to="/" end className="nav-link tienda-enlace">Productos</NavLink>
              <NavLink to="/carrito" className="nav-link tienda-enlace">Mi carrito</NavLink>
            </nav>
          </div>
        </div>
      </header>

      <main className="container py-4 py-md-5 flex-grow-1">
        <Routes>
          <Route path="/" element={<ProductoListar />} />
          <Route path="/producto/:id" element={<ProductoDetalles />} />
          <Route path="/carrito" element={<Carrito />} />
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