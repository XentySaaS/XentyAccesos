/**
 * Campo de contraseña con "ojito" para mostrar/ocultar lo tecleado.
 *
 * No debilita la seguridad: el valor solo se revela en pantalla a quien ya lo está escribiendo
 * (riesgo = mirada ajena, y lo controla el usuario). Reduce errores de captura, sobre todo en
 * móvil. Sirve también para otros secretos (API keys, HMAC). El toggle usa type="button" para
 * no disparar el submit del formulario.
 */
import { InputHTMLAttributes, useState } from "react";
import { Eye, EyeOff } from "lucide-react";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type">;

export default function InputPassword({ className, ...props }: Props) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <input {...props} type={visible ? "text" : "password"} className={`${className ?? ""} pr-10`} />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
        title={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
        className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-slate-400 transition hover:text-slate-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
}
