document.addEventListener("DOMContentLoaded", () => {
    const menuButton = document.getElementById("menuButton");
    const sidebar = document.getElementById("sidebar");

    if (menuButton && sidebar) {
        menuButton.addEventListener("click", () => {
            sidebar.classList.toggle("open");
        });
    }

    const passwordToggle = document.getElementById("passwordToggle");
    const passwordInput = document.getElementById("password");

    if (passwordToggle && passwordInput) {
        passwordToggle.addEventListener("click", () => {
            const hidden = passwordInput.type === "password";

            passwordInput.type = hidden ? "text" : "password";

            passwordToggle.innerHTML = hidden
                ? '<i class="bi bi-eye-slash"></i>'
                : '<i class="bi bi-eye"></i>';
        });
    }

    const chartCanvas = document.getElementById("overviewChart");

    if (chartCanvas && window.dashboardData) {
        new Chart(chartCanvas, {
            type: "bar",
            data: {
                labels: ["Students", "Teachers", "Courses", "Enrollments"],
                datasets: [{
                    label: "Total",
                    data: [
                        window.dashboardData.students,
                        window.dashboardData.teachers,
                        window.dashboardData.courses,
                        window.dashboardData.enrollments
                    ],
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        },
                        grid: {
                            drawBorder: false
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
});
