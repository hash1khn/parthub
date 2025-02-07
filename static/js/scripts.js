let savedVehicles = [];  // Store vehicles for search

// Fetch saved vehicles from the backend
async function fetchSavedVehicles() {
  const response = await fetch("/api/saved_vehicles");
  savedVehicles = await response.json();
  displaySavedVehicles(savedVehicles);
}

// Display vehicles after search
function displaySavedVehicles(vehicles) {
  const storedData = document.getElementById("storedData");
  storedData.innerHTML = "";

  vehicles.forEach(vehicle => {
    const item = document.createElement("div");
    item.classList.add("stored-item");
    item.innerHTML = `
      <div>
        <span>${vehicle.minYear || ''} - ${vehicle.maxYear || ''} ${vehicle.make} ${vehicle.model}</span>
        <span>Part: ${vehicle.part}</span>
        <button class="edit-btn" onclick="editVehicle(${vehicle.id})">
        <img src="/static/assets/editbutton.jpg" alt="edit"></button>
        <button class="delete-btn" onclick="deleteVehicle(${vehicle.id})">
        <img src="/static/assets/deletebutton.png" alt="delete"></button>
      </div>
    `;
    storedData.appendChild(item);
  });
}

// Handle form submission for saving a new vehicle
document.getElementById("carFilterForm").addEventListener("submit", async function(event) {
  event.preventDefault();

  const formData = {
    make: document.getElementById("make").value,
    model: document.getElementById("model").value,
    minYear: document.getElementById("minYear").value,
    maxYear: document.getElementById("maxYear").value,
    part: document.getElementById("part").value
  };

  await fetch("/api/saved_vehicles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formData)
  });

  this.reset();
  fetchSavedVehicles();  // Refresh the list of saved vehicles
});

// Delete a vehicle by ID
async function deleteVehicle(id) {
  await fetch(`/api/saved_vehicles/${id}`, { method: "DELETE" });
  fetchSavedVehicles();  // Refresh after deleting
}

// Edit an existing vehicle's details
async function editVehicle(id) {
  const vehicle = savedVehicles.find(v => v.id === id); // Find vehicle by id

  // Populate the modal with the current vehicle data
  document.getElementById("editVehicleId").value = vehicle.id;
  document.getElementById("editMake").value = vehicle.make;
  document.getElementById("editModel").value = vehicle.model;
  document.getElementById("editMinYear").value = vehicle.minYear;
  document.getElementById("editMaxYear").value = vehicle.maxYear;
  document.getElementById("editPart").value = vehicle.part;

  // Show the modal
  $('#editVehicleModal').modal('show');
}

// Handle form submission for editing a vehicle
document.getElementById("editVehicleForm").addEventListener("submit", async function(event) {
  event.preventDefault();

  const updatedVehicle = {
    make: document.getElementById("editMake").value,
    model: document.getElementById("editModel").value,
    minYear: document.getElementById("editMinYear").value,
    maxYear: document.getElementById("editMaxYear").value,
    part: document.getElementById("editPart").value
  };

  const vehicleId = document.getElementById("editVehicleId").value;

  // Send the updated vehicle data to the backend
  const response = await fetch(`/api/saved_vehicles/${vehicleId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(updatedVehicle)
  });

  const result = await response.json();
  if (result.message) {
    alert("Vehicle updated successfully!");
    $('#editVehicleModal').modal('hide');  // Hide the modal after successful update
    fetchSavedVehicles();  // Refresh the saved vehicles list
  } else {
    alert("Failed to update vehicle!");
  }
});

// Search vehicles based on the input in the search bar
async function searchVehicles() {
    const searchQuery = document.getElementById("searchBar").value.toLowerCase();

    // Call the search API with the query
    const response = await fetch(`/api/search_vehicles?query=${searchQuery}`);
    const vehicles = await response.json();

    displaySavedVehicles(vehicles);  // Display filtered list
}

// Clear the search bar and reset the displayed vehicles
function clearSearch() {
    document.getElementById("searchBar").value = '';
    fetchSavedVehicles();  // Display all vehicles
}

// Initial fetch of saved vehicles when the page loads
fetchSavedVehicles();