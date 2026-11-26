import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "react-toastify";
import { api } from "../../api/Api";

export const RestablecerPassword = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [passwordConfirmacion, setPasswordConfirmacion] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (password !== passwordConfirmacion) {
      toast.error("Las contraseñas no coinciden");
      return;
    }

    api.post("password-reset/confirm/", {
      token,
      password,
      password_confirmacion: passwordConfirmacion,
    })
      .then(() => {
        toast.success("Contraseña actualizada. Inicia sesión.");
        navigate("/login");
      })
      .catch((err) => {
        toast.error(err.response?.data?.error || "Enlace inválido o expirado");
      });
  };

  return (
    <section className="registro py-4 py-md-5">
      <header className="mb-4">
        <p className="registro-sobretitulo mb-2">Recuperar acceso</p>
        <h1 className="registro-titulo mb-3">NUEVA CONTRASEÑA</h1>
        <p className="registro-texto">
          Debe incluir al menos una mayúscula, una minúscula, un número y un símbolo.
        </p>
      </header>

      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="new-pass" className="form-label">
            Nueva Contraseña
          </label>
          <input
            id="new-pass"
            type="password"
            className="form-control"
            placeholder="Ingresa tu Nueva Contraseña"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        <div className="mb-4">
          <label htmlFor="new-pass-confirm" className="form-label">
            Confirmar Contraseña
          </label>
          <input
            id="new-pass-confirm"
            type="password"
            className="form-control"
            placeholder="Repite tu Contraseña"
            autoComplete="new-password"
            value={passwordConfirmacion}
            onChange={(e) => setPasswordConfirmacion(e.target.value)}
            required
          />
        </div>

        <div className="registro-pie mt-5">
          <button type="submit" className="btn registro-boton">
            Cambiar Contraseña
          </button>
          <p className="registro-texto small mb-0">
            <Link to="/login">Volver a Iniciar Sesión</Link>
          </p>
        </div>
      </form>
    </section>
  );
};