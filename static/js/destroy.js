import { apiDelete, apiGet } from "./api.js";

const products = document.getElementById("product-destroy")
const message = document.getElementById("destroy_confirm")
const confirm = document.getElementById("destroy")
const csrfToken = document.body.dataset.csrf

async function fetchProducts() {
    const data = await apiGet("/api/products/")
    products.innerHTML = data.results.map(p => `
        <option value="${p.id}">${p.sku} - ${p.name}</option>    
    `).join("")
}

confirm.addEventListener("click", async (event) => {

    const prod_to_del = Number(products.value)

    try {
        await apiDelete(`/api/products/${prod_to_del}/`, csrfToken)
        message.textContent = "destroyed"
        fetchProducts()
    } catch (error) {
        message.textContent = error.message
    }
})



fetchProducts()