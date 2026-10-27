import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { api } from "../api/Api";

export const MiCuenta = () => {
  const [cuenta, setCuenta] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("mi-cuenta/")
      .then((response) => {
        setCuenta(response.data);
      })
      .catch((error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          navigate("/login");
        } else {
          toast.error("No se Pudieron Cargar tus Datos.");
        }
      })
      .finally(() => {
        setCargando(false);
      });
  }, [navigate]);

  const cambiarCampo = (e) => {
    setCuenta({
      ...cuenta,
      [e.target.name]: e.target.value,
    });
  };

  const guardarCambios = (e) => {
    e.preventDefault();
    setGuardando(true);

    api.patch("mi-cuenta/", {
      nombre: cuenta.nombre,
      apellido: cuenta.apellido,
      email:cuenta.email,
      telefono: cuenta.telefono,
      direccion: cuenta.direccion,
    })
      .then((response) => {
        setCuenta(response.data);
        toast.success("Tus Datos se Actualizaron Correctamente.");
      })
      .catch((error) => {
        const respuesta = error.response?.data;

        const mensaje =
          respuesta && typeof respuesta === "object"
            ? Object.values(respuesta).flat().join(" ")
            : "No se Pudieron Guardar los Cambios.";

        toast.error(mensaje, { autoClose: 8000 });
      })
      .finally(() => {
        setGuardando(false);
      });
  };

  if (cargando) {
    return <p className="text-center py-5">Cargando tu Cuenta...</p>;
  }

  if (!cuenta) {
    return (
      <div className="text-center py-5">
        <p>No se Pudieron Cargar los Datos de tu Cuenta.</p>
      </div>
    );
  }

  return (
    <section className="registro py-4">
      <header className="mb-5">
        <p className="registro-sobretitulo mb-2">Tu Información</p>
        <h1 className="registro-titulo mb-3">Mi Cuenta</h1>
        <p className="registro-texto mb-0">Consulta y Actualiza tus Datos.</p>
      </header>

      <dl className="row g-3 mb-5">
        <div className="col-md-6">
          <dt className="small registro-texto">RUT</dt>
          <dd className="mb-0">{cuenta.rut}</dd>
        </div>
      </dl>

      <form onSubmit={guardarCambios}>
        <div className="row g-4">
            <div className="col-md-6">
            <label htmlFor="cuenta-nombre" className="form-label">Nombre</label>
            <input
                id="cuenta-nombre"
                name="nombre"
                type="text"
                className="form-control"
                autoComplete="given-name"
                maxLength={150}
                value={cuenta.nombre}
                onChange={cambiarCampo}
                required
            />
            </div>

            <div className="col-md-6">
            <label htmlFor="cuenta-apellido" className="form-label">Apellido</label>
            <input
                id="cuenta-apellido"
                name="apellido"
                type="text"
                className="form-control"
                autoComplete="family-name"
                maxLength={150}
                value={cuenta.apellido}
                onChange={cambiarCampo}
                required
            />
            </div>

            <div className="col-12">
            <label htmlFor="cuenta-email" className="form-label">Correo electrónico</label>

            <input
                id="cuenta-email"
                name="email"
                type="email"
                className="form-control"
                autoComplete="email"
                maxLength={254}
                value={cuenta.email}
                onChange={cambiarCampo}
                required
            />
            </div>

            <div className="col-md-6">
            <label htmlFor="cuenta-telefono" className="form-label">Teléfono <span className="registro-opcional">(opcional)</span></label>

            <div className="input-group">
                <span className="input-group-text">+56</span>
                <input
                id="cuenta-telefono"
                name="telefono"
                type="tel"
                inputMode="tel"
                className="form-control"
                autoComplete="tel-national"
                placeholder="912345678"
                value={cuenta.telefono.replace(/^\+56/, "")}
                onChange={cambiarCampo}
                />
            </div>
                <p className="form-text mb-0">Ingresa los 9 Dígitos del Número.</p>
            </div>

            <div className="col-12">
            <label htmlFor="cuenta-direccion" className="form-label">Dirección <span className="registro-opcional">(opcional)</span></label>
            <input
                id="cuenta-direccion"
                name="direccion"
                type="text"
                className="form-control"
                autoComplete="street-address"
                placeholder="Calle, número, departamento o casa"
                maxLength={200}
                value={cuenta.direccion}
                onChange={cambiarCampo}
            />
            </div>
        </div>

        <div className="registro-pie mt-5">
          <button
            type="submit"
            className="btn registro-boton"
            disabled={guardando}
          >
            {guardando ? "Guardando..." : "Guardar cambios"}
          </button>

          <Link to="/catalogo">Volver al Catálogo</Link>
        </div>
      </form>
    </section>
  );
};