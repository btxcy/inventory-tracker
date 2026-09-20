import { apiGet } from "./api.js";

// get all products for list in dashboard
async function fetchProducts() {
    const data = await apiGet("/api/products/")
    render(data.results)
}

function render(products) {
    const tbody = document.getElementById("product-rows");
    tbody.innerHTML = products.map(p => `
        <tr>
        <td>${p.sku}</td>
        <td>${p.name}</td>
        <td>${p.category_name}</td>
        <td>${p.quantity}</td>
        <td>${p.reorder_level}</td>
        </tr>
    `).join("")
}

fetchProducts();
