# ruff: noqa: E501
import os
from textwrap import dedent
from typing import TYPE_CHECKING

import httpx
from mcp.server.fastmcp import FastMCP

from task_messager import __version__

if TYPE_CHECKING:
    from task_messager.models import Domain

DOMAINS: "dict[str, Domain]" = {
    "backend": {
        "label": "Backend",
        "analysis_steps": [
            {
                "title": "API / Endpoint İnceleme",
                "detail": "İlgili endpoint'in request/response logları ve HTTP durum kodları incelenir.",
            },
            {
                "title": "Veritabanı Sorgusu",
                "detail": "Yavaş veya hatalı sorgular EXPLAIN/ANALYZE ile analiz edilir; index kullanımı kontrol edilir.",
            },
            {
                "title": "Kuyruk & Async İşlem",
                "detail": "Message queue (SQS, RabbitMQ vb.) backlog, dead-letter kayıtları ve consumer hataları gözden geçirilir.",
            },
            {
                "title": "Servis Bağımlılıkları",
                "detail": "Downstream servislerin sağlık durumu (health-check) ve timeout değerleri doğrulanır.",
            },
            {
                "title": "Bulgu Paylaşımı",
                "detail": "Kök neden ve önerilen düzeltme teknik dille raporlanır.",
            },
        ],
        "acceptance_criteria": [
            "Hatalı endpoint veya servis tespit edilmiş ve logları alınmıştır.",
            "Veritabanı tarafında anomali olup olmadığı netleştirilmiştir.",
            "Sorunun kaynağı (kod hatası, config, altyapı) belirlenmiştir.",
            "Düzeltme önerisi veya geçici workaround talep sahibine iletilmiştir.",
        ],
    },
    "frontend": {
        "label": "Frontend",
        "analysis_steps": [
            {
                "title": "Tarayıcı & Ortam Tespiti",
                "detail": "Sorunun hangi tarayıcı/versiyon ve işletim sisteminde oluştuğu belirlenir.",
            },
            {
                "title": "Console & Network İnceleme",
                "detail": "DevTools console hataları ve başarısız network istekleri (4xx/5xx) analiz edilir.",
            },
            {
                "title": "State & Render Kontrolü",
                "detail": "Bileşen state'i, props akışı ve gereksiz re-render'lar React/Vue DevTools ile incelenir.",
            },
            {
                "title": "Performans Profili",
                "detail": "Lighthouse veya DevTools Performance sekmesiyle LCP, CLS, FID metrikleri ölçülür.",
            },
            {
                "title": "Bulgu Paylaşımı",
                "detail": "Reproducing adımları ve ekran görüntüleriyle birlikte rapor hazırlanır.",
            },
        ],
        "acceptance_criteria": [
            "Sorun belirli tarayıcı/cihaz kombinasyonunda tekrarlanabilir hale getirilmiştir.",
            "Console hatası veya network isteği kök nedeni tespit edilmiştir.",
            "Düzeltme PR'ı açılmış ya da geçici CSS/JS fix uygulanmıştır.",
            "Analiz raporu ve ekran görüntüleri talep sahibine iletilmiştir.",
        ],
    },
    "devops": {
        "label": "DevOps / Altyapı",
        "analysis_steps": [
            {
                "title": "Pipeline & Build İnceleme",
                "detail": "CI/CD pipeline logları (GitHub Actions, GitLab CI vb.) adım adım incelenir; hatalı stage belirlenir.",
            },
            {
                "title": "Container & Orchestration",
                "detail": "Docker container logları, exit code'lar ve restart politikası kontrol edilir.",
            },
            {
                "title": "Altyapı Kaynakları",
                "detail": "CPU, bellek, disk ve ağ metrikleri (CloudWatch, Grafana vb.) anomali açısından incelenir.",
            },
            {
                "title": "Güvenlik & Erişim",
                "detail": "IAM izinleri, Security Group kuralları ve secret/env değişkenleri doğrulanır.",
            },
            {
                "title": "Bulgu Paylaşımı",
                "detail": "RCA (Root Cause Analysis) ve iyileştirme önerisi runbook formatında paylaşılır.",
            },
        ],
        "acceptance_criteria": [
            "Pipeline veya deployment hatası tam log çıktısıyla belgelenmiştir.",
            "Altyapı kaynak tüketimi anomalisi tespit edilmiş veya dışlanmıştır.",
            "Güvenlik açığı veya yanlış config varsa düzeltilmiş ya da bilet açılmıştır.",
            "Servis başarıyla yeniden deploy edilmiş ve sağlık kontrolü geçmiştir.",
        ],
    },
    "mobile": {
        "label": "Mobil",
        "analysis_steps": [
            {
                "title": "Crash & Hata Raporu",
                "detail": "Firebase Crashlytics / Sentry üzerinden stack trace ve etkilenen cihaz/OS versiyonları incelenir.",
            },
            {
                "title": "Build & Sürüm Kontrolü",
                "detail": "Uygulama versiyonu, build numarası ve bağımlılık versiyonları doğrulanır.",
            },
            {
                "title": "API & Bağlantı Testi",
                "detail": "Mobil taraftan gelen API isteklerinin başarı oranı ve timeout değerleri kontrol edilir.",
            },
            {
                "title": "Store Kural Uyumu",
                "detail": "App Store / Google Play politika değişiklikleri ve inceleme geri bildirimleri gözden geçirilir.",
            },
            {
                "title": "Bulgu Paylaşımı",
                "detail": "Etkilenen cihaz/OS matrisi ve düzeltme planı talep sahibine iletilir.",
            },
        ],
        "acceptance_criteria": [
            "Crash stack trace'i alınmış ve kök neden belirlenmiştir.",
            "Sorunun belirli OS versiyonu veya cihazla sınırlı olup olmadığı netleştirilmiştir.",
            "Düzeltme içeren yeni build hazırlanmış veya hotfix planı oluşturulmuştur.",
            "Analiz sonucu talep sahibine ve varsa store ekibine iletilmiştir.",
        ],
    },
    "data": {
        "label": "Veri / Analytics",
        "analysis_steps": [
            {
                "title": "Pipeline Sağlığı",
                "detail": "ETL/ELT pipeline'ının durum logları (Airflow, dbt vb.) incelenir; başarısız tasklar ve gecikmeler tespit edilir.",
            },
            {
                "title": "Veri Kalitesi Kontrolü",
                "detail": "Kaynak ve hedef veri setleri arasında null oranları, veri tipleri ve aykırı değerler (outlier) analiz edilir.",
            },
            {
                "title": "Storage & Bağlantı",
                "detail": "Veritabanı/Data Warehouse bağlantıları, sorgu performansı ve depolama kapasitesi kontrol edilir.",
            },
            {
                "title": "Raporlama & Metrikleri",
                "detail": "BI araçları (Tableau, Power BI vb.) raporlarının güncel olup olmadığı ve hesaplamaları doğrulanır.",
            },
            {
                "title": "Bulgu Paylaşımı",
                "detail": "Veri anomalisi ve düzeltme planı veri ekibine ve ilgili paydaşlara iletilir.",
            },
        ],
        "acceptance_criteria": [
            "Pipeline hatası tam ayrıntılı loglarla belgelenmiştir.",
            "Veri kalitesi sorusu (eksik, yanlış, geç veri) tespit edilmiş veya dışlanmıştır.",
            "Etkilenen raporlar ve metrikler belirlenmiştir.",
            "Düzeltme veya geçici workaround uygulanmış sosyal medya kullanıcılarına bildirilmiştir.",
        ],
    },
    "business": {
        "label": "İşletme / Proses",
        "analysis_steps": [
            {
                "title": "Gereksinim Analizi",
                "detail": "İstenilen görev, hedef ve başarı ölçütleri paydaşlarla netleştirilir.",
            },
            {
                "title": "Mevcut Durum Değerlendirmesi",
                "detail": "Mevcut belgeler, süreçler ve altyapı incelenir; boşluklar ve iyileştirme fırsatları tespit edilir.",
            },
            {
                "title": "Çözüm Tasarımı",
                "detail": "Önerilen yeni belgeler, iş akışları veya araçlar tasarlanır; maliyet-fayda analizi yapılır.",
            },
            {
                "title": "Uygulama Planı",
                "detail": "Adım adım uygulama takvimi, sorumlu taraflar ve kontrol noktaları tanımlanır.",
            },
            {
                "title": "Bulgu Paylaşımı",
                "detail": "Özetlenmiş rapor ve uygulanabilir öneriler yöneticilere ve ilgili ekiplere sunulur.",
            },
        ],
        "acceptance_criteria": [
            "Görev gereksinimleri ve başarı kriterleri yazılı olarak onaylanmıştır.",
            "Mevcut durum analizi tamamlanmış ve iyileştirme alanları belirlenmiştir.",
            "Çözüm önerisi ve uygulama planı hazırlanmıştır.",
            "Plan paydaşlarca gözden geçirilmiş ve kabul edilmiştir.",
        ],
    },
    "general": {
        "label": "Genel",
        "analysis_steps": [
            {
                "title": "Sorgulama",
                "detail": "İletilen bilgiler kullanılarak mevcut durum ve bağlam netleştirilir.",
            },
            {
                "title": "Log Analizi",
                "detail": "İlgili sistem loglarından hata ve anomaliler incelenir.",
            },
            {
                "title": "Bağımlılık Kontrolü",
                "detail": "Üçüncü taraf servisler ve entegrasyonlar sağlık durumu açısından değerlendirilir.",
            },
            {
                "title": "Bulgu Paylaşımı",
                "detail": "Tespit edilen anomali veya çözüm önerisi teknik dille raporlanır.",
            },
        ],
        "acceptance_criteria": [
            "Sorunun kapsamı ve etki alanı belirlenmiştir.",
            "Kök neden (kullanıcı hatası mı, yazılım bug'ı mı, altyapı mı) netleştirilmiştir.",
            "Analiz sonucu ve çözüm önerisi talep sahibine iletilmiştir.",
        ],
    },
}


app = FastMCP(
    name="task-mcp",
    instructions=dedent("""
        You are a helpful assistant that formats support investigation tasks
        into structured messages and sends them to a Google Chat space via webhook.

        Available domains / task types:
          - backend   : API, database, queue, microservice issues
          - frontend  : UI bug, rendering, performance, browser compatibility
          - devops    : CI/CD, infrastructure, Docker, cloud, deployment
          - mobile    : iOS/Android crash, build, store submission
          - data      : Data pipeline, ETL, analytics, reporting issues
          - business  : Non-technical tasks like documentation, process improvement, etc.
          - general   : Catch-all when domain is unclear

        When the user describes a task, pick the most suitable domain so that
        domain-specific investigation steps and acceptance criteria are pre-filled.
        The user can override any field explicitly.

        CRITICAL - task_owner vs participants rules:
          - task_owner is WHO THE TASK IS ASSIGNED TO (the responsible person).
          - participants are OBSERVERS / STAKEHOLDERS who are mentioned but are NOT the assignee.
          - If the user says "bana aç" or does not specify → task_owner = TASK_OWNER env var (the requester themselves).
          - If the user says "Ali'ye aç" or "Ali'ye ver" → task_owner = "Ali", even if others are mentioned.
          - If the user says "katılımcılar: X, Y" or "CC: X, Y" or "ekle: X, Y" → those go to participants, NOT task_owner.
          - NEVER assign the task to participants. The task is always owned by a single task_owner.
          - participants is a separate field shown as "Katılımcılar" in the card — it is purely informational.

        Always confirm the filled-in card details before sending unless the user
        explicitly says "gönder" or "send directly".
    """),
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "8000")),
)


httpx_client = httpx.AsyncClient(
    headers={"User-Agent": f"MCP-Task-Messager/{__version__}"},
    timeout=httpx.Timeout(15.0, connect=10.0),
)
