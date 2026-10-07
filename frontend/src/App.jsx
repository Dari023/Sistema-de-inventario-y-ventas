import { Routes, Route, Link } from "react-router-dom";
import { ProductoListar } from "./modules/ProductoListar";
import { ProductoDetalles } from "./modules/ProductoDetalles";
import { Carrito } from "./modules/Carrito";
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

export const App = () => {
  return (
    <div>
      <ToastContainer position="top-right" autoClose={2000} />
      <h1>Sistema de Inventario y Ventas</h1>
      <nav>
        <Link to="/">Productos</Link> | <Link to="/carrito">Carrito</Link>
      </nav>
      <hr />
      
      
      <Routes>
        <Route path="/" element={<ProductoListar />} />
        <Route path="/producto/:id" element={<ProductoDetalles />} />
        <Route path="/carrito" element={<Carrito />} />
      </Routes>
      
    </div>
  );
};