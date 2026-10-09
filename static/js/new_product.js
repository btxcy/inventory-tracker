import { apiPost, apiGet } from "./api.js";

const csrfToken = document.body.dataset.csrf
const sku = document.getElementById("sku")
const name = document.getElementById("new-product-name")
const description_text = document.getElementById("description")
const category_select = document.getElementById("category-select")
const supplier_select = document.getElementById("supplier-select")
const unit = document.getElementById("unit")
const cost_price = document.getElementById("cost-price")
const sale_price = document.getElementById("sale-price")
const quantity = document.getElementById("quantity")
const reorder_level = document.getElementById("reorder-level")
const reorder_quantity = document.getElementById("reorder-quantity")
const confirm_create = document.getElementById("confirm-create-new")

const message = document.getElementById("create-confirm-message")

// get all categories
async function fetchCategory() {
    const data = await apiGet("/api/categories/")
    category_select.innerHTML = data.results.map(c => `
        <option value="${c.id}">${c.name}</option>    
    `).join("")
}

// get all suppliers
async function fetchSupplier() {
    const data = await apiGet("/api/suppliers/")
    supplier_select.innerHTML = data.results.map(s => `
        <option value="${s.id}">${s.name} - ${s.email}</option>    
    `).join("")
}

// press save button
confirm_create.addEventListener("click", async (event) => {

    const body = {
        sku: sku.value,
        name: name.value,
        description: description_text.value,
        category: category_select.value,
        supplier: supplier_select.value,
        unit: unit.value,
        cost_price: cost_price.value,
        sale_price: sale_price.value,
        opening_quantity: quantity.value,
        reorder_level: reorder_level.value,
        reorder_quantity: reorder_quantity.value,
    }

    try {
        await apiPost("/api/products/", body, csrfToken)
        message.textContent = "created"
    } catch (error) {
        message.textContent = error.message
    }

})

fetchCategory()
fetchSupplier()