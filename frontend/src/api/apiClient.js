import axios from 'axios';

// 🚀 这里会自动根据环境切换 URL
const apiClient = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL,
    headers: {
        'Content-Type': 'application/json'
    }
});

export default apiClient;