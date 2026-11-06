import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from 'react-toastify';
import { api } from "../api/Api";

export const Login = () => {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const navigate = useNavigate();

    const handleSubmit = (e) => {
        e.preventDefault();
        api.post("login/", { email, password })
            .then((response) => {
                localStorage.setItem("access_token", response.data.access);
                localStorage.setItem("refresh_token", response.data.refresh);
                toast.success("Bienvenido a la tienda");
                navigate("/");
            })
            .catch(() => toast.error("Credenciales incorrectas"));
    };

    return (
        <section className="registro login-tienda py-4 py-md-5">
            <header className="mb-5">
                <p className="registro-sobretitulo mb-2">Tu Cuenta</p>
                <h1 className="registro-titulo mb-3">INICIA SESIÓN</h1>
                <p className="registro-texto mb-0">
                    Accede a tu cuenta para continuar con tus compras.
                </p>
            </header>

            <form onSubmit={handleSubmit}>
                <div className="mb-4">
                    <label htmlFor="login-email" className="form-label">
                        Correo Electrónico
                    </label>
                    <input
                        id="login-email"
                        type="email"
                        className="form-control"
                        placeholder="nombre@gmail.com"
                        autoComplete="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                </div>

                <div className="mb-4">
                    <label htmlFor="login-password" className="form-label">
                        Contraseña
                    </label>
                    <input
                        id="login-password"
                        type="password"
                        className="form-control"
                        placeholder="Ingresa tu Contraseña"
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />
                </div>

                <div className="registro-pie mt-5">
                    <button type="submit" className="btn registro-boton">
                        Iniciar Sesión
                    </button>

                    <p className="registro-texto small mb-0">
                        ¿No tienes una Cuenta?{" "}
                        <Link to="/registro">Regístrate</Link>
                    </p>
                </div>
            </form>
        </section>
    );
};