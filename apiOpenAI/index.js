// index.js

import 'dotenv/config'; // <--- Asegúrate que esta línea esté al inicio
import OpenAI from "openai"; 

// El cliente de OpenAI busca automáticamente la clave en process.env.OPENAI_API_KEY
// ¡NO NECESITAS PASAR EL PARÁMETRO apiKey!
const client = new OpenAI(); 

async function runTest() {
    try {
        // Tu ejemplo de llamada a la API
        const response = await client.chat.completions.create({
            model: "gpt-4-turbo",
            messages: [
                { role: "user", content: "Hola, dime qué es Node.js en una frase" }
            ]
        });
        
        // La respuesta de la API es un objeto, no un string directo, así que cambia cómo accedes al texto:
        console.log(response.choices[0].message.content); // <--- Corrección aquí
    
    } catch (error) {
        console.error("Error en la llamada a OpenAI:", error);
    }
}

runTest(); // Llama a la función para que se ejecute