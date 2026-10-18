import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from 'react-toastify';
import { api } from "../api/Api";

export const Login = () => {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const navigate = useNavigate();

    const handleSubmit = (e) => {
        e.preventDefault();
        api.post("login/", { username, password })
            .then((response) => {
                localStorage.setItem("access_token", response.data.access);
                localStorage.setItem("refresh_token", response.data.refresh);
                toast.success("Bienvenido a la tienda");
                navigate("/");
            })
            .catch(() => toast.error("Credenciales incorrectas"));
    };

    return (
        <div>
            <h2>Iniciar Sesión</h2>
            <form onSubmit={handleSubmit}>
                <div>
                    <input type="text" placeholder="Usuario" onChange={(e) => setUsername(e.target.value)} required />
                </div>
                <div style={{ margin: "10px 0" }}>
                    <input type="password" placeholder="Contraseña" onChange={(e) => setPassword(e.target.value)} required />
                </div>
                <button type="submit">Ingresar</button>
            </form>
        </div>
    );
};