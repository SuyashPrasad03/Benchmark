document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const competitorListDiv = document.getElementById('competitor-list');
    const selectAllCheckbox = document.getElementById('selectAll');
    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const submitButton = document.getElementById('submit-button');
    const loadingOverlay = document.getElementById('loading-overlay');
    const resultsArea = document.getElementById('results-area');
    const tableContainer = document.getElementById('table-container');
    const graphContainer = document.getElementById('graph-container');
    const graphToggle = document.getElementById('graph-toggle');
    const chartCanvas = document.getElementById('comparison-chart');

    let comparisonChart = null;

    // --- 1. Fetch and Display Available Companies ---
    const fetchCompanies = async () => {
        try {
            const response = await fetch('/api/available-companies');
            if (!response.ok) throw new Error('Failed to fetch company list');
            const data = await response.json();

            competitorListDiv.innerHTML = ''; // Clear previous
            data.companies.forEach(company => {
                // Don't show Tata Steel as a selectable competitor
                if (company !== 'Tata Steel') {
                    const item = document.createElement('div');
                    item.className = 'competitor-item';
                    item.innerHTML = `
                        <input type="checkbox" id="company-${company}" name="competitor" value="${company}">
                        <label for="company-${company}">${company}</label>
                    `;
                    competitorListDiv.appendChild(item);
                }
            });
        } catch (error) {
            competitorListDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
        }
    };

    // --- 2. Handle Form Submission ---
    queryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const selectedCompetitors = Array.from(document.querySelectorAll('input[name="competitor"]:checked')).map(cb => cb.value);
        
        if (selectedCompetitors.length === 0) {
            alert('Please select at least one competitor to compare.');
            return;
        }

        loadingOverlay.classList.remove('hidden');
        resultsArea.classList.add('hidden');
        submitButton.disabled = true;

        try {
            const response = await fetch('/api/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: queryInput.value,
                    competitors: selectedCompetitors,
                    base_company: 'Tata Steel'
                }),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'An API error occurred.');
            }

            const results = await response.json();
            displayResults(results);

        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            loadingOverlay.classList.add('hidden');
            submitButton.disabled = false;
        }
    });

    // --- 3. Display Results (Table and Graph) ---
    const displayResults = (data) => {
        if (!data || !data.table_data || !data.graph_data) {
            alert('Received invalid data from the server.');
            return;
        }
        
        // Render Table
        renderTable(data.table_data);

        // Render Graph
        renderGraph(data.graph_data);

        resultsArea.classList.remove('hidden');
    };

    const renderTable = (tableData) => {
        if (tableData.length === 0) {
            tableContainer.innerHTML = '<p>No data found for the given query.</p>';
            return;
        }
        const headers = Object.keys(tableData[0]);
        let tableHTML = '<table border="1"><thead><tr>';
        headers.forEach(h => tableHTML += `<th>${h}</th>`);
        tableHTML += '</tr></thead><tbody>';

        tableData.forEach(row => {
            tableHTML += '<tr>';
            headers.forEach(header => {
                tableHTML += `<td>${row[header]}</td>`;
            });
            tableHTML += '</tr>';
        });

        tableHTML += '</tbody></table>';
        tableContainer.innerHTML = tableHTML;
    };

    const renderGraph = (graphData) => {
        if (comparisonChart) {
            comparisonChart.destroy();
        }
        comparisonChart = new Chart(chartCanvas, {
            type: 'bar', // or 'line'
            data: graphData,
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Company Comparison: ' + queryInput.value
                    }
                }
            }
        });
        // Handle initial toggle state
        graphContainer.style.display = graphToggle.checked ? 'block' : 'none';
    };

    // --- 4. UI Event Listeners ---
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', (e) => {
            document.querySelectorAll('input[name="competitor"]').forEach(checkbox => {
                checkbox.checked = e.target.checked;
            });
        });
    }

    graphToggle.addEventListener('change', (e) => {
        graphContainer.style.display = e.target.checked ? 'block' : 'none';
    });

    // --- Initial Load ---
    fetchCompanies();
});