
---

## ** Jenerik Arama Pipeline **

```markdown
# Jenerik Arama Pipeline

Bu pipeline, çeşitli kaynaklardan yapısal ve sistematik bilgiler toplar.

## Örnek Kullanım
```python
from pipelines.jenerik_pipeline.main import run_pipeline

query = "İstanbul'daki fullstack developerlar"
results = run_pipeline(query)
print(results)
