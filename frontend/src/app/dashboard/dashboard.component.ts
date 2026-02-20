import { Component, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { DashboardService } from './dashboard.service';

@Component({
    selector: 'app-dashboard',
    standalone: true,
    imports: [CommonModule, RouterLink],
    providers: [DashboardService],
    templateUrl: './dashboard.component.html',
    styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {
    // Signals for storing API data
    summary = signal<any>({
        totalSignalsMonitored: 0,
        activeAlerts: 0,
        orchestratorStatus: 'Offline',
        systemUptimeSeconds: 0
    });

    severity = signal<any>({
        high: 0,
        medium: 0,
        low: 0
    });

    alerts = signal<any[]>([]);
    loading = signal(false);
    error = signal<string | null>(null);

    // Modal State
    selectedAlert = signal<any>(null);
    showModal = signal(false);

    // Search State
    searchTerm = signal('');

    constructor(private dashboardService: DashboardService) { }

    ngOnInit() {
        this.refreshDashboard();
    }

    refreshDashboard() {
        this.loading.set(true);

        // ForkJoin-like pattern with signals (chained for simplicity or parallel)
        this.dashboardService.getSummary().subscribe({
            next: (data) => this.summary.set(data),
            error: (err) => console.error('Summary error', err)
        });

        this.dashboardService.getSeverity().subscribe({
            next: (data) => this.severity.set(data),
            error: (err) => console.error('Severity error', err)
        });

        this.dashboardService.getAlerts().subscribe({
            next: (data) => {
                this.alerts.set(data);
                this.loading.set(false);
            },
            error: (err) => {
                this.error.set('Failed to load dashboard data');
                this.loading.set(false);
            }
        });
    }

    // Helper for Uptime formatting
    formatUptime(seconds: number): string {
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        return `${hrs}h ${mins}m`;
    }

    // Modal Actions
    viewExplanation(alert: any) {
        this.selectedAlert.set(alert);
        this.showModal.set(true);
    }

    closeModal() {
        this.showModal.set(false);
        this.selectedAlert.set(null);
    }

    // Helper for Severity
    getSeverityNum(severity: any): number {
        if (typeof severity === 'number') return severity;
        if (severity === 'High') return 0.8;
        if (severity === 'Medium') return 0.5;
        return 0.2;
    }

    // Filtered Alerts getter
    get filteredAlerts() {
        const term = this.searchTerm().toLowerCase();
        if (!term) return this.alerts();
        return this.alerts().filter(a =>
            a.signalName.toLowerCase().includes(term) ||
            a.impactSummary.toLowerCase().includes(term)
        );
    }
}
