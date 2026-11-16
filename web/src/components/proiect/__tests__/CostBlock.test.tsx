// @vitest-environment jsdom
// The cost block must never show the partial sum of priced lines as the cost of the project.
import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { Cost } from '@/api/models'
import { CostBlock } from '@/components/proiect/parts'

const base: Cost = {
  suficient: false, moneda: 'RON', ipoteze: [], referinte_folosite: [], motiv: 'Niciun proiect de referință nu are atât costul, cât și suprafața publicate.',
  suma_cotata_lei: 133728, articole_cotate: 4, articole_necotate: ['bazin principal', 'turn cu tobogane acvatice'], pe_surse: { seap: 4 },
  eticheta_suma: 'Suma articolelor cotate (4 din 14); 10 articole rămân de cotat', metoda: '',
  titlu: 'Cost total: nu poate fi estimat din datele disponibile', lipsesc_principale: true,
  nota_suma: 'Suma nu include elementele principale ale amenajării.',
}

afterEach(cleanup)

describe('CostBlock', () => {
  it('says the total cannot be estimated and keeps the partial sum in a secondary block', () => {
    render(<CostBlock cost={base} />)
    expect(screen.getByText('Cost total: nu poate fi estimat din datele disponibile')).toBeTruthy()
    expect(screen.getByText(base.motiv!)).toBeTruthy()
    const partial = screen.getByTestId('suma-partiala')
    expect(within(partial).getByText('Informație parțială')).toBeTruthy()
    expect(within(partial).getByText(base.eticheta_suma!)).toBeTruthy()
    expect(within(partial).getByText('Suma nu include elementele principale ale amenajării.')).toBeTruthy()
    expect(within(partial).getByText('bazin principal')).toBeTruthy()
    expect(within(partial).getByText('turn cu tobogane acvatice')).toBeTruthy()
    // the figure exists only inside the secondary block, and nothing calls it the cost of the project
    expect(screen.getAllByText(/133\.728/)).toHaveLength(1)
    expect(within(partial).getByText(/133\.728/)).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/costul proiectului/i)
  })

  it('shows the reference interval as the headline when it exists', () => {
    render(<CostBlock cost={{ ...base, suficient: true, motiv: null, min_lei: 61700, mediana_lei: 140300, max_lei: 490100, titlu: 'Cost estimat din proiecte de referință', lipsesc_principale: false, nota_suma: null }} />)
    expect(screen.getByText('Cost estimat din proiecte de referință')).toBeTruthy()
    expect(screen.getByText(/140\.300/)).toBeTruthy()
    expect(screen.queryByText('Suma nu include elementele principale ale amenajării.')).toBeNull()
  })

  it('has no partial block when no line is priced', () => {
    render(<CostBlock cost={{ ...base, suma_cotata_lei: 0, articole_cotate: 0, pe_surse: {}, nota_suma: null }} />)
    expect(screen.queryByTestId('suma-partiala')).toBeNull()
    expect(screen.getByText(/Niciun articol din lista de materiale nu are încă o sursă de preț/)).toBeTruthy()
  })
})
