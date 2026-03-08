
---

## ** Lokal Firma Arama Pipeline (Google Maps) **

```markdown
# Lokal Firma Arama Pipeline

Bu pipeline, belirli bir lokasyondaki firmaları ve mekanları bulmayı amaçlar.

## Örnek Kullanım
```python
from pipelines.lokalfirma_pipeline.main import run_pipeline

query = "Şişli'deki dişçiler"
results = run_pipeline(query)
print(results)
