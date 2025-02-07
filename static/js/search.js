// Store the original full car listings when the page is first loaded
let originalCarListings = "";

// Function to fetch and display the filtered cars
async function searchCars() {
    const query = document.getElementById("searchInput").value;
    const response = await fetch(`/api/search_cars?query=${query}`);
    const vehicles = await response.json();
    displayCarListings(vehicles);
}

// Function to clear the search and restore the original car listings
function clearSearch() {
    document.getElementById("searchInput").value = "";  // Clear the search input
    // Simply restore the original car listings to the view
    document.getElementById("carListings").innerHTML = originalCarListings;
}

// Function to display the car listings dynamically
function displayCarListings(vehicles) {
    const carListings = document.getElementById("carListings");
    carListings.innerHTML = "";  // Clear previous listings
    
    if (vehicles.length === 0) {
        carListings.innerHTML = "<p>No cars found.</p>";
        return;
    }

    // Create and append the table for displaying filtered cars
    const table = document.createElement("table");
    table.classList.add("table", "table-striped");
    
    const tableHeader = document.createElement("thead");
    tableHeader.innerHTML = `
        <tr>
            <th>Year</th>
            <th>Make</th>
            <th>Model</th>
            <th>Row</th>
            <th>Date</th>
            <th>Yard</th>
        </tr>
    `;
    table.appendChild(tableHeader);

    const tableBody = document.createElement("tbody");
    vehicles.forEach(vehicle => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${vehicle.year}</td>
            <td>${vehicle.make}</td>
            <td>${vehicle.model}</td>
            <td>${vehicle.row}</td>
            <td>${vehicle.date}</td>
            <td>${vehicle.yard}</td>
        `;
        tableBody.appendChild(row);
    });

    table.appendChild(tableBody);
    carListings.appendChild(table);
}

// Listen for the 'Enter' key press to trigger the search
document.getElementById("searchInput").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();  // Prevent form submission (if inside a form)
        searchCars();  // Trigger the search when Enter is pressed
    }
});
async function refreshDatabase() {
    document.getElementById("statusMessage").innerHTML = "Refreshing database... Please wait.";

    try {
        const response = await fetch("/api/refresh_database", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });

        const data = await response.json();
        document.getElementById("statusMessage").innerHTML = data.message;
        fetchUpdatedData(); // Reload updated data
    } catch (error) {
        console.error("Error refreshing database:", error);
        document.getElementById("statusMessage").innerHTML = "Error updating database.";
    }
}

// Ensure that the original car listings are saved when the page is loaded
window.addEventListener('load', function() {
    originalCarListings = document.getElementById("carListings").innerHTML;
});
