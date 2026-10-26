import { apiGet, apiPost } from "./api.js";

const form = document.getElementById("movement-form");
const message = document.getElementById("message");
const product_select = document.getElementById("product-select")

async function fetchProducts() {
    const data = await apiGet("/api/products/?page_size=200")
    console.log(data)
    product_select.innerHTML = data.results.map(p => `
        <option value="${p.id}">${p.sku} - ${p.name}</option>
    `).join("")
}

// use form
form.addEventListener("submit", async (event) => {
    event.preventDefault()

    const formData = new FormData(form) // create form

    const body = {
        product: Number(formData.get("product")),
        movement_type: formData.get("movement_type"),
        quantity: Number(formData.get("quantity")),
        reference: formData.get("reference"),
    }

    try {
        await apiPost("/api/movements/", body, formData.get("csrfmiddlewaretoken"))
        message.textContent = "saved"
        form.reset()
    } catch (error) {
        message.textContent = error.message
    }
})

fetchProducts()
