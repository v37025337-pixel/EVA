# Аудит и исправление ядра YADO — 19 сентября 2026

Проверенная реализация: `YADO_UNIFIED_KERNEL_REPAIR_V2`, runtime `V4_MAINTENANCE_R2`. Формальное поколение: `G2_CANDIDATE_TRCG_V1`.

Область проверки: 106 исходников активного ядра, 9 слоёв, 34 зарегистрированные возможности, 131 workflow; отдельно проверены границы записи 60 текущих writer-workflow.

## Исправления

| Область | Исправление |
|---|---|
| STATE_SNAPSHOT | Consistent SQLite read snapshots and preserve caller-owned transaction boundaries. |
| STATE_APPEND | Revalidate causal state inside write transaction before legacy submit. |
| REPLAY_VERIFICATION | Recompute verification semantics; reject forged PASS and boolean-as-integer answers. |
| SOURCE_PROVENANCE | Re-emit native source from original training and strategy before restoring executable memory. |
| ORACLE_ISOLATION | Execute external expression oracles in bounded worker; reject decorated/default/top-level code. |
| PUBLIC_LIBRARY_TRANSPORT | Pin validated public address and TLS host; reject redirects and private transport. |
| REPAIR_INPUT | Require bounded source, nonempty typed examples and matching function contract. |
| TYPED_ADMISSION | Require actual boolean hard constraints and revalidate mutable admission inputs. |
| NATIVE_REFRESH | Refresh one effective learned binding idempotently; remove stale duplicate assignments. |
| EXPERIENCE_PERSISTENCE | Bind learning facts, receipt, capability and current execution identity; reject source and destination symlinks. |
| LEARNING_SEQUENCE | Use same-run verified public experience in isolated native refresh; measure ranking effect without claiming transfer gain. |
| UNIFIED_WORKFLOWS | Route three obsolete deep-development entry points to the current shared workflow. |
| WORKFLOW_WRITES | Enforce four shadow branch destinations and reject source movement in two evidence writers. |
| SECURITY_EVIDENCE | Require fresh complete dependency evidence, actual source scan coverage and exact dynamic-site review. |
| WORKFLOW_POLICY | Reconcile 131 workflows/60 scoped writers; pin 37 action references to official immutable commits. |
| DEPENDENCIES | Upgrade aiohttp 3.13.5 to 3.14.3; eliminate 14 unique known advisory IDs in fresh audit. |
| REPORT_LIFECYCLE | Invalidate previous regression PASS before git, manifest loading, collection or execution; preserve the real log artifact. |

## Доказательства

- Полная регрессия в GitHub Actions: **594/594 PASS**, без пропусков и изменений исходников в ходе прогона.
- Полный аудит ядра V2, канон, ledger и связи модулей: **PASS**.
- Security: **PASS**; 33 зависимости, **0 известных уязвимостей** на момент свежей проверки.
- Проверены 131 YAML и 884 shell-блока. Четыре проверки записи включают реальный локальный Git-сценарий с изменившейся веткой.
- Проверки отрицательных случаев воспроизвели дефекты до исправления; они включены в общий регрессионный набор.

Отчёт привязан к исходникам `69059d90` и проверенному merge commit `eb977662`. Финальная проверка выполнена на чистом Ubuntu в GitHub Actions. Локальные прерванные запуски и DNS-ошибки не засчитаны как успех.

## Канон и ограничения

История V3/V4 и прежний опыт сохранены. Опыт из feed-run 35436941759 и 35439259316 архивирован отдельно с точными commit и hash. Исправления внесены ассистентом по запросу пользователя; автоматическое повышение кандидатов в канон не разрешено.

Аудит конечен: его PASS подтверждает перечисленные проверки, а не отсутствие всех возможных неизвестных дефектов. Изменение ранжирования само по себе не доказывает прирост способности. Перехода в G3 и утверждения о сознании нет.

Машиночитаемые результаты: [validation](yado-unified-kernel-repair-v2-validation.json), [regression](yado-full-regression-v1-report.json), [kernel](yado-full-kernel-audit-v2-report.json), [security](yado-security-audit-v1-report.json), [workflow review](yado-workflow-write-review-v2.json).

## Финальный CI и обучение

Все **19 workflow завершились успешно**. [PR #119](https://github.com/v37025337-pixel/EVA/pull/119) объединяет исправления и доказательства.

[Полная регрессия](https://github.com/v37025337-pixel/EVA/actions/runs/35440133987): **594/594**, без пропусков. [Security](https://github.com/v37025337-pixel/EVA/actions/runs/35440134101): 33 зависимости, 0 известных уязвимостей. [Обучение и продолжение](https://github.com/v37025337-pixel/EVA/actions/runs/35440134021): **20+5 циклов**, прежние события сохранены точно, цели выбраны из состояния ядра.

Свежие данные успешно загружены, но новых фактов и изменения ранжирования в этом запуске нет (`NO_MEASURED_BEHAVIOR_GAIN`). Прирост способности не заявлен.

Полные первичные артефакты находятся в GitHub Actions; в репозитории сохранены точные JSON-выводы и метаданные их привязки. Две незавершённые локальные попытки отмечены WITHHOLD; финальные результаты получены независимо на чистом Ubuntu CI.
