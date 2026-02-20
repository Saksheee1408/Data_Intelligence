import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
    providedIn: 'root'
})
export class DashboardService {
    private apiUrl = 'http://localhost:8000/api/dashboard';

    constructor(private http: HttpClient) { }

    getSummary(): Observable<any> {
        return this.http.get(`${this.apiUrl}/summary`);
    }

    getSeverity(): Observable<any> {
        return this.http.get(`${this.apiUrl}/severity`);
    }

    getAlerts(limit: number = 20): Observable<any[]> {
        return this.http.get<any[]>(`${this.apiUrl}/alerts?limit=${limit}`);
    }
}
