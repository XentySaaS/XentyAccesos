import axios from "axios";

// La landing solo llama al endpoint público de alta (signup) del control plane.
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "/" });

export default api;
