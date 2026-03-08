# Spesifik Bilgi Arama Pipeline

Bu pipeline, daraltılmış ve spesifik bir bilgiye ulaşmayı amaçlar.

## Örnek Kullanım
```python
from pipelines.spesifik_pipeline.main import run_pipeline

query = "Galatasaray'ın 2025 yılında attığı gollerin detayları"
results = run_pipeline(query)
print(results)
