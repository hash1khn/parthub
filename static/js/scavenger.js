document.addEventListener("DOMContentLoaded", function () {
    fetchYardData("all"); // Load data on page load
});

// Function to fetch yards and Hot Wheels cars from Flask API
function fetchYardData(filterDays) {
    // Store which yards are expanded
    const expandedYards = {};
    document.querySelectorAll(".vehicles-list").forEach(yardElement => {
        if (yardElement.style.display === "block") {
            expandedYards[yardElement.id] = true;
        }
    });

    fetch(`/api/scavenger_filtered?days=${filterDays}`)
        .then(response => response.json())
        .then(data => {
            renderYards(data, expandedYards);
        })
        .catch(error => console.error("Error fetching yards:", error));
}

// Function to render yards dynamically
function renderYards(yardsData, expandedYards) {
    const scavengerContainer = document.getElementById("scavengerContainer");
    scavengerContainer.innerHTML = ""; // Clear previous data

    Object.entries(yardsData).forEach(([yardName, yard]) => {
        // Create Yard Section
        const yardSection = document.createElement("div");
        yardSection.classList.add("yard-section");

        const yardHeader = `
            <div class="yard-header" onclick="toggleYard('${yardName}')">
                <h2>${yardName}</h2>
                <span class="hot-wheels-count">${yard.hotWheelsCount}</span>
            </div>
            <div id="yard-${yardName}" class="vehicles-list" style="display: ${expandedYards[`yard-${yardName}`] ? "block" : "none"};"></div>
        `;
        yardSection.innerHTML = yardHeader;

        scavengerContainer.appendChild(yardSection);

        // Create Vehicle Rows
        const vehiclesList = document.getElementById(`yard-${yardName}`);
        yard.vehicles.forEach(([rowNumber, cars]) => {
            cars.forEach((vehicle) => {
                console.log("checkinggg",vehicle)
                const vehicleRow = document.createElement("div");
                vehicleRow.classList.add("vehicle-row");

                // Apply completed styling
                if (vehicle.completed) {
                    vehicleRow.classList.add("completed");
                }

                vehicleRow.innerHTML = `
                    <span class="vehicle-row-number">Row: ${vehicle.row}</span>
                    <span class="vehicle-models">${vehicle.year} ${vehicle.make} ${vehicle.model}</span>
                    <input 
                        type="checkbox" 
                        class="vehicle-checkbox" 
                        ${vehicle.completed ? "checked" : ""}  
onchange="toggleRowCompletion('${yardName}', ${vehicle.row}, '${vehicle.make}', '${vehicle.model}', ${vehicle.year}, this.checked)"
                    />
                `;
                vehiclesList.appendChild(vehicleRow);
            });
        });
    });
}

// Function to toggle row completion (now checks by row & year)
function toggleRowCompletion(yard, row, make, model, year, isChecked) {
    console.log("DEBUG: ", { yard, row, make, model, year, isChecked });

    if (!yard || !row || !make || !model || !year) {
        console.error("❌ ERROR: Missing parameters in toggleRowCompletion.");
        return;
    }

    // Encode parameters to ensure they are URL-safe
    let encodedYard = encodeURIComponent(yard);
    let encodedMake = encodeURIComponent(make);
    let encodedModel = encodeURIComponent(model);
    let encodedRow = encodeURIComponent(row);
    let encodedYear = encodeURIComponent(year);

    fetch(`/api/scavenger_yards/${encodedYard}/rows/${encodedRow}/vehicles/${encodedMake}/${encodedModel}/${encodedYear}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ completed: isChecked })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("✅ Updated Vehicle:", data);

        // Find the checkbox and update its state dynamically
        document.querySelectorAll(".vehicle-row").forEach(rowElement => {
            let rowNumber = rowElement.querySelector(".vehicle-row-number").innerText;
            let modelInfo = rowElement.querySelector(".vehicle-models").innerText;

            if (rowNumber.includes(row) && modelInfo.includes(`${year} ${make} ${model}`)) {
                let checkbox = rowElement.querySelector(".vehicle-checkbox");
                checkbox.checked = data.completed;

                if (data.completed) {
                    rowElement.classList.add("completed");
                } else {
                    rowElement.classList.remove("completed");
                }
            }
        });
    })
    .catch(error => console.error("❌ Error updating vehicle:", error));
}





// Function to filter vehicles by age
function filterVehicles(filterType) {
    fetchYardData(filterType);
}

// Function to toggle yard visibility
function toggleYard(yardName) {
    const yardElement = document.getElementById(`yard-${yardName}`);
    if (yardElement.style.display === "none") {
        yardElement.style.display = "block";
    } else {
        yardElement.style.display = "none";
    }
}
