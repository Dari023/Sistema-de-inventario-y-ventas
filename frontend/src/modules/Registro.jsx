import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { api } from "../api/Api";

export const Registro = () => {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [passwordConfirmacion, setPasswordConfirmacion] = useState("");
    const [rut, setRut] = useState("");
    const [nombre, setNombre] = useState("");
    const [apellido, setApellido] = useState("");
    const [telefono, setTelefono] = useState("");
    const [direccion, setDireccion] = useState("");
    const navigate = useNavigate();
    const passwordEvaluada = password.trim();
    const requisitosPassword = [
    {
        texto: "Tener al Menos 8 Caracteres.",
        cumplido: [...passwordEvaluada].length >= 8,
    },
    {
        texto: "Incluir al Menos una Mayúscula.",
        cumplido: /\p{Lu}/u.test(passwordEvaluada),
    },
    {
        texto: "Incluir al Menos una Minúscula.",
        cumplido: /\p{Ll}/u.test(passwordEvaluada),
    },
    {
        texto: "Incluir al Menos un Número.",
        cumplido: /\p{Nd}/u.test(passwordEvaluada),
    },
    {
        texto: "Incluir al Menos un Símbolo",
        cumplido: /[^\p{L}\p{N}\s]/u.test(passwordEvaluada),
    },
    ];
    const passwordCumple = requisitosPassword.every(
    (requisito) => requisito.cumplido
    );

    const passwordsCoinciden =
        passwordConfirmacion.length > 0 &&
        password === passwordConfirmacion;

    const cambiarTelefono = (e) => {
        let numero = e.target.value.replace(/[\s()-]/g, "");

        if (numero.startsWith("+56")) {
            numero = numero.slice(3);
        } else if (/^56[0-9]{9}$/.test(numero)) {
            numero = numero.slice(2);
        }

        setTelefono(numero);
        };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!passwordCumple || !passwordsCoinciden) {
            return;
        }
        
        api.post("registro/", { email, password, password_confirmacion: passwordConfirmacion, rut, nombre, apellido, telefono, direccion })
            .then(() => {
                toast.success("Registro exitoso. Ahora puedes iniciar sesión.");
                navigate("/login");
            })
            .catch((err) => {
                const respuesta = err.response?.data;

                const mensaje =
                    respuesta && typeof respuesta === "object"
                    ? Object.values(respuesta).flat().join(" ")
                    : "No pudimos registrar tu cuenta. Inténtalo nuevamente.";

                toast.error(mensaje, {
                    autoClose: 8000,
                });
            });
    };

    return (
        <main className="registro py-4 py-md-5">
            <header className="mb-5">
            <p className="registro-sobretitulo mb-2">Tu Cuenta</p>
            <h1 className="registro-titulo mb-3">CREA TU CUENTA</h1>
            <p className="registro-texto mb-0">Completa tus datos para registrarte en nuestra tienda.</p>
            </header>

            <form onSubmit={handleSubmit}>
            <fieldset className="mb-5">
                <legend className="registro-seccion">Datos Personales</legend>

                <div className="row g-4">
                <div className="col-md-6">
                    <label htmlFor="registro-nombre" className="form-label">Nombre</label>
                    <input
                    id="registro-nombre"
                    type="text"
                    className="form-control"
                    placeholder="Tu Nombre"
                    autoComplete="given-name"
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    required
                    />
                </div>

                <div className="col-md-6">
                    <label htmlFor="registro-apellido" className="form-label">Apellido</label>
                    <input
                    id="registro-apellido"
                    type="text"
                    className="form-control"
                    placeholder="Tu Apellido"
                    autoComplete="family-name"
                    value={apellido}
                    onChange={(e) => setApellido(e.target.value)}
                    required
                    />
                </div>

                <div className="col-md-6">
                    <label htmlFor="registro-rut" className="form-label">RUT</label>
                    <input
                    id="registro-rut"
                    type="text"
                    className="form-control"
                    placeholder="12345678-5"
                    value={rut}
                    onChange={(e) => setRut(e.target.value)}
                    required
                    />
                    <p className="form-text mb-0">Sin Puntos y con Guion.</p>
                </div>
                </div>
            </fieldset>

            <fieldset className="mb-5">
                <legend className="registro-seccion">Información de Contacto</legend>
                <div className="row g-4">
                <div className="col-md-6">
                    <label htmlFor="registro-email" className="form-label">Correo Electrónico</label>
                    <input
                    id="registro-email"
                    type="email"
                    className="form-control"
                    placeholder="nombre@gmail.com"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    />
                </div>

                <div className="col-md-6">
                    <label htmlFor="registro-telefono" className="form-label">Teléfono 
                        <span className="registro-opcional"> (Opcional)</span>
                    </label>
                    <div className="input-group">
                    <span className="input-group-text">+56</span>
                    <input
                        id="registro-telefono"
                        type="tel"
                        inputMode="tel"
                        autoComplete="tel-national"
                        className="form-control"
                        placeholder="912345678"
                        value={telefono}
                        onChange={cambiarTelefono}
                    />
                    </div>
                    <p className="form-text mb-0">Ingresa los 9 dígitos de tu Número.</p>
                </div>

                <div className="col-12">
                    <label htmlFor="registro-direccion" className="form-label">Dirección 
                        <span className="registro-opcional"> (Opcional)</span>
                    </label>
                    <input
                    id="registro-direccion"
                    type="text"
                    className="form-control"
                    placeholder="Calle, número, departamento o casa"
                    autoComplete="street-address"
                    maxLength={200}
                    value={direccion}
                    onChange={(e) => setDireccion(e.target.value)}
                    />
                </div>
                </div>
            </fieldset>

            <fieldset className="mb-4">
                <legend className="registro-seccion">Contraseña de Acceso</legend>
                <div className="row g-4">
                <div className="col-md-6">
                    <label htmlFor="password" className="form-label">Contraseña</label>
                    <input
                    id="password"
                    type="password"
                    className="form-control"
                    placeholder="Crea tu Contraseña"
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    />
                </div>

                <div className="col-md-6">
                    <label htmlFor="password-confirmacion" className="form-label">Confirmar Contraseña</label>
                    <input
                    id="password-confirmacion"
                    type="password"
                    className="form-control"
                    placeholder="Repite tu Contraseña"
                    autoComplete="new-password"
                    value={passwordConfirmacion}
                    onChange={(e) => setPasswordConfirmacion(e.target.value)}
                    required
                    />

                    {passwordConfirmacion.length > 0 && (
                    <p
                        className={`small mt-2 mb-0 ${
                        passwordsCoinciden ? "text-success" : "text-danger"
                        }`}
                    >
                        {passwordsCoinciden
                        ? "✓ Las contraseñas coinciden."
                        : "Las contraseñas no coinciden."}
                    </p>
                    )}
                </div>
                </div>

                <div className="mt-4">
                <p className="registro-texto small mb-2">Requisitos de la Contraseña</p>
                <ul className="registro-requisitos">
                    {requisitosPassword.map((requisito) => (
                    <li
                        key={requisito.texto}
                        className={
                        requisito.cumplido
                            ? "text-success"
                            : password.length > 0
                            ? "text-danger"
                            : "text-secondary"
                        }
                    >
                        <span className="registro-indicador">
                        {requisito.cumplido ? "✓" : "○"}
                        </span>

                        {requisito.texto}
                    </li>
                    ))}
                </ul>
                </div>
            </fieldset>

            <div className="registro-pie mt-5">
                <button type="submit" className="btn registro-boton" disabled={!passwordCumple || !passwordsCoinciden}>Crear mi Cuenta</button>
                <p className="registro-texto small mb-0">¿Ya tienes una Cuenta?{" "}<Link to="/login">Inicia Sesión</Link></p>
            </div>
            </form>
        </main>
        );
};