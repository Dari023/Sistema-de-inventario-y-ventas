import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { api } from "../api/Api";

export const Registro = () => {
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [rut, setRut] = useState("");
    const [nombre, setNombre] = useState("");
    const [apellido, setApellido] = useState("");
    const [telefono, setTelefono] = useState("");
    const [direccion, setDireccion] = useState("");
    const navigate = useNavigate();

    const handleSubmit = (e) => {
        e.preventDefault();
        api.post("registro/", { username, email, password, rut, nombre, apellido, telefono, direccion })
            .then(() => {
                toast.success("Registro exitoso. Ahora puedes iniciar sesión.");
                navigate("/login");
            })
            .catch((err) => {
                const errores = err.response?.data;
                const mensaje = errores
                    ? Object.values(errores).flat().join(" ")
                    : "Error al registrar el cliente. Verifica los datos.";
                toast.error(mensaje);
            });
    };

    return (
        <div>
            <h2>Crear Cuenta de Cliente</h2>
            <form onSubmit={handleSubmit}>
                <div>
                    <input type="text" placeholder="Nombre de usuario" onChange={(e) => setUsername(e.target.value)} required />
                </div>
                <div style={{ margin: "10px 0" }}>
                    <input type="email" placeholder="Correo electrónico" onChange={(e) => setEmail(e.target.value)} required />
                </div>
                <div>
                    <input type="password" placeholder="Contraseña" onChange={(e) => setPassword(e.target.value)} required />
                </div>

                <h4>Datos Personales</h4>
                <div style={{ margin: "10px 0" }}>
                    <input type="text" placeholder="RUT (ej: 12345678-9)" onChange={(e) => setRut(e.target.value)} required />
                </div>
                <div>
                    <input type="text" placeholder="Nombre" onChange={(e) => setNombre(e.target.value)} required />
                </div>
                <div style={{ margin: "10px 0" }}>
                    <input type="text" placeholder="Apellido" onChange={(e) => setApellido(e.target.value)} required />
                </div>
                <div>
                    <input type="text" placeholder="Teléfono" onChange={(e) => setTelefono(e.target.value)} />
                </div>
                <div style={{ margin: "10px 0" }}>
                    <input type="text" placeholder="Dirección" onChange={(e) => setDireccion(e.target.value)} />
                </div>

                <button type="submit">Registrarse</button>
            </form>
        </div>
    );
};
