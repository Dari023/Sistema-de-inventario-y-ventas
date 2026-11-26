import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/Api";

export const RecuperarPassword = () => {
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    api.post("password-reset/", { email }).finally(() => setEnviado(true));
  };

  if (enviado) {
    return (
      <section className="registro py-4 py-md-5">
        <header className="mb-4">
          <p className="registro-sobretitulo mb-2">Recuperar acceso</p>
          <h1 className="registro-titulo mb-3">Revisa tu correo</h1>
          <p className="registro-texto">
            Si <strong>{email}</strong> está registrado, te enviamos un enlace
            para crear una nueva contraseña
          </p>
        </header>
        <Link to="/login">Volver a Iniciar Sesión</Link>
      </section>
    );
  }

  return (
    <section className="registro py-4 py-md-5">
      <header className="mb-4">
        <p className="registro-sobretitulo mb-2">Recuperar acceso</p>
        <h1 className="registro-titulo mb-3">¿OLVIDASTE TU CONTRASEÑA?</h1>
        <p className="registro-texto">Ingresa tu correo y te enviaremos un enlace para crear una nueva</p>
      </header>

      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="reset-email" className="form-label">
            Correo Electrónico
          </label>
          <input
            id="reset-email"
            type="email"
            className="form-control"
            placeholder="nombre@gmail.com"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="registro-pie mt-5">
          <button type="submit" className="btn registro-boton">
            Enviar Enlace
          </button>
          <p className="registro-texto small mb-0">
            <Link to="/login">Volver a Iniciar Sesión</Link>
          </p>
        </div>
      </form>
    </section>
  );
};