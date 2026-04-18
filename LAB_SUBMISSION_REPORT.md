# דוח הגשה — מעבדת תשתית Proxmox (test.local)

**שם:** __________________  
**תאריך:** __________________  

מסמך זה מסכם את ביצוע הדרישות: רשת פרטית, נתב עם NAT, DNS סמכותי (BIND), GitLab CE + Runner, תחנת פיתוח, K3s, ואפליקציית Flask עם CI/CD ופריסה ל-Kubernetes.

> **הערה:** הוסף קבצי PNG (או JPG) לתיקייה `screenshots/` לפי השמות המוצעים למטה, או עדכן את הנתיבים ב-`![תיאור](...)` בהתאם. אם אין תמונה — השאר את השורה; ב-PDF אפשר להדביק תמונות ידנית.

---

## 0. סקירה כללית — תשתית הפרויקט

### מה להראות בצילום מסך

| # | קובץ מוצע | תוכן הצילום |
|---|-----------|-------------|
| 0.1 | `screenshots/00-proxmox-vms.png` | Proxmox — רשימת ה-VMs (Ubuntu 22.04): router, dns, gitlab, dev, k3s עם מצב Running |
| 0.2 | `screenshots/00-network-topology.png` | (אופציונלי) סכימת רשת ידנית או `ip -br a` על הנתב והמארח |

### הסבר קצר

כל ה-VMs הן Ubuntu 22.04 ב-KVM, חברות ברשת פרטית `10.20.30.0/24` למעט ממשק ה-WAN של הנתב. כל המכונות מוגדרות עם **שער** `10.20.30.1` ו-**DNS** `10.20.30.250` (כפי שמופיע ב-inventory ובתפקיד `common`).

| תפקיד | FQDN | כתובת |
|--------|------|--------|
| נתב | router.test.local | 10.20.30.1 (+ ממשק אינטרנט) |
| DNS | dns.test.local | 10.20.30.250 |
| GitLab | gitlab.test.local | 10.20.30.100 |
| תחנת פיתוח | dev.test.local | 10.20.30.99 |
| K3s | k3s.test.local | 10.20.30.200 |

![Proxmox — VMs](screenshots/00-proxmox-vms.png)

---

## 1. נתב (Router)

### דרישות: שני ממשקים, routing, NAT ליציאה לאינטרנט

### מה להראות בצילום מסך

| # | קובץ מוצע | תוכן הצילום |
|---|-----------|-------------|
| 1.1 | `screenshots/01-router-ip.png` | `ip -br a` או `ip addr` — ממשק LAN (למשל 10.20.30.1/24) וממשק WAN (DHCP/כתובת ציבורית פנימית) |
| 1.2 | `screenshots/01-router-nat.png` | `sudo nft list ruleset` או תוכן `nftables` — שרשרת `nat` עם `masquerade` על ממשק היציאה |
| 1.3 | `screenshots/01-router-forwarding.png` | `sysctl net.ipv4.ip_forward` → `1` |

### הסבר קצר

הנתב מחבר את הרשת הפרטית לאינטרנט: **IP forwarding** מופעל, ו-**NAT (masquerade)** מתרגם כתובות פנימיות ביציאה דרך ממשק האינטרנט, כך שמכונות ב-`10.20.30.0/24` יכולות לגלוש החוצה בלי כתובת ציבורית משלהן.

![ממשקי נתב](screenshots/01-router-ip.png)

![NAT nftables](screenshots/01-router-nat.png)

---

## 2. שרת DNS (BIND)

### דרישות: שרת סמכותי לדומיין test.local — חיפוש קדימה ואחורה

### מה להראות בצילום מסך

| # | קובץ מוצע | תוכן הצילום |
|---|-----------|-------------|
| 2.1 | `screenshots/02-dns-forward.png` | `dig @10.20.30.250 gitlab.test.local +short` → `10.20.30.100` (או FQDN אחר מהטבלה) |
| 2.2 | `screenshots/02-dns-reverse.png` | `dig @10.20.30.250 -x 10.20.30.100 +short` → שם PTR צפוי (למשל `gitlab.test.local.`) |
| 2.3 | `screenshots/02-bind-status.png` | `systemctl status named` או `bind9` — active |

### הסבר קצר

BIND מוגדר כ-**authoritative** לדומיין `test.local` (רשומות A) ולאזור **הפוך** לרשת `10.20.30.0/24` (רשומות PTR), כך שגם שם→כתובת וגם כתובת→שם עובדים מתוך הרשת הפרטית.

![חיפוש קדימה](screenshots/02-dns-forward.png)

![חיפוש הפוך](screenshots/02-dns-reverse.png)

---

## 3. GitLab

### דרישות: GitLab CE עדכני, משתמש developer, Runner על אותה מכונה

### מה להראות בצילום מסך

| # | קובץ מוצע | תוכן הצילום |
|---|-----------|-------------|
| 3.1 | `screenshots/03-gitlab-login.png` | דף התחברות GitLab בכתובת `http://gitlab.test.local` |
| 3.2 | `screenshots/03-gitlab-developer-user.png` | Admin → Users — משתמש **developer** קיים |
| 3.3 | `screenshots/03-gitlab-runner.png` | Settings → CI/CD → Runners — runner רשום ופעיל (executor shell או לפי ההגדרה בפרויקט) |
| 3.4 | `screenshots/03-registry.png` | `curl -s http://gitlab.test.local:5050/v2/` או מסך Container Registry בפרויקט |

### הסבר קצר

GitLab Community Edition מותקן על `gitlab.test.local`. נוצר משתמש **developer** לעבודה שוטפת. **GitLab Runner** רשום לאותה מכונה ומריץ pipelines (בפרויקט זה לרוב runner מסוג `shell` עם Docker). **Container Registry** על פורט **5050** משמש לאחסון תמונות שנבנו ב-CI.

![משתמש developer](screenshots/03-gitlab-developer-user.png)

---

## 4. תחנת פיתוח (Workstation)

### דרישות: Docker CE, Git, משתמש developer, מפתחות SSH, העלאת מפתח ל-GitLab

### מה להראות בצילום מסך

| # | קובץ מוצע | תוכן הצילום |
|---|-----------|-------------|
| 4.1 | `screenshots/04-docker-version.png` | `docker --version` ו-`sudo docker run hello-world` (או `docker ps`) |
| 4.2 | `screenshots/04-git-version.png` | `git --version` |
| 4.3 | `screenshots/04-developer-user.png` | `id developer` / `getent passwd developer` |
| 4.4 | `screenshots/04-ssh-key.png` | `ls -la /home/developer/.ssh/` — `id_rsa` / `id_rsa.pub` |
| 4.5 | `screenshots/04-gitlab-ssh-key.png` | GitLab → developer → SSH Keys — המפתח הציבורי מוצג כרשום |

### הסבר קצר

על **dev.test.local** מותקנים **Docker Engine (CE)** ו-**Git**. המשתמש **developer** משמש לפיתוח; נוצרו לו **מפתחות SSH ברירת מחדל**, והמפתח הציבורי הועלה לפרופיל GitLab של **developer** כדי לאפשר `git push` ב-SSH.

![מפתח ב-GitLab](screenshots/04-gitlab-ssh-key.png)

---

## 5. K3s — אשכול צומת בודד

### מה להראות בצילום מסך

| # | קובץ מוצע | תוכן הצילום |
|---|-----------|-------------|
| 5.1 | `screenshots/05-kubectl-nodes.png` | `kubectl get nodes` — צומת אחד במצב **Ready** |
| 5.2 | `screenshots/05-k3s-service.png` | `systemctl status k3s` על `k3s.test.local` (אופציונלי) |

### הסבר קצר

על **k3s.test.local** הותקן **K3s** כאשכול **single-node**. מ-**dev.test.local** (כמשתמש developer עם `kubeconfig`) ניתן לנהל את האשכול.

![kubectl get nodes](screenshots/05-kubectl-nodes.png)

---

## 6. כמשתמש developer — פרויקט `word` ו-CI/CD

### 6.1 מאגר Git תחת `/home/developer/word`

### מה להראות בצילום מסך

| # | קובץ מוצע | תוכן הצילום |
|---|-----------|-------------|
| 6.1 | `screenshots/06-word-ls.png` | `ls -la /home/developer/word` — קבצי פרויקט (app, Dockerfile, `.gitlab-ci.yml`) |

### הסבר קצר

נוצר פרויקט Git תחת **`/home/developer/word`**, מחובר ל-remote ב-GitLab (אין צורך להגיש את ה-repo עצמו אם המדריך מאשר — מספיק צילום מסך של התיקייה וההיסטוריה המקומית או דף הפרויקט ב-GitLab).

![תוכן תיקיית word](screenshots/06-word-ls.png)

---

### 6.2 שירות Flask — מילה אקראית בהפעלה, `GET /` מחזיר אותה

### מה להראות בצילום מסך

| # | קובץ מוצע | תוכן הצילום |
|---|-----------|-------------|
| 6.2a | `screenshots/06-app-py.png` | עורך או `cat` — קטע מ-`app.py`: טעינת מילון, בחירה אקראית בזמן עלייה, `GET /` מחזיר JSON עם `word` ו-`hostname` |
| 6.2b | `screenshots/06-curl-local.png` | `curl -s http://127.0.0.1:5000/` (אחרי הרצה מקומית) או דרך ה-NodePort אחרי הפריסה |

### הסבר קצר

האפליקציה קוראת מילים מקובץ מילון סטנדרטי (`/usr/share/dict/words` בקונטיינר), בוחרת **מילה אחת אקראית בעת ההפעלה** ושומרת אותה במשתנה גלובלי. בכל קריאה ל-**`GET /`** מוחזר אותו ערך (ב-JSON). קיים גם **`GET /health`** לבדיקות מוכנות ב-Kubernetes.

---

### 6.3 Dockerfile

### מה להראות בצילום מסך

| # | קובץ מוצע | תוכן הצילום |
|---|-----------|-------------|
| 6.3 | `screenshots/06-dockerfile.png` | תוכן `Dockerfile` — base image, התקנת תלויות, `COPY`, `EXPOSE`, `CMD` |

### הסבר קצר

ה-**Dockerfile** בונה image שמריץ את שירות ה-Flask על פורט 5000, כולל התקנת חבילות Python והעתקת הקוד.

---

### 6.4 GitLab CI — בנייה עם מספר commit ודחיפה ל-Registry פנימי

### מה להראות בצילום מסך

| # | קובץ מוצע | תוכן הצילום |
|---|-----------|-------------|
| 6.4a | `screenshots/06-gitlab-ci-yml.png` | `.gitlab-ci.yml` — שלב build, `docker build` עם `$CI_COMMIT_SHORT_SHA`, `docker push` ל-registry |
| 6.4b | `screenshots/06-pipeline-success.png` | GitLab → CI/CD → Pipelines — pipeline ירוק |
| 6.4c | `screenshots/06-registry-tags.png` | Container Registry של הפרויקט — תגים כולל **commit short SHA** ו-**latest** |

### הסבר קצר

ה-pipeline מתחבר ל-**GitLab Container Registry**, בונה תמונה מתויגת ב-**`$CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA`** (ומעלה גם **`latest`**), ודוחף לרג'יסטרי הפנימי (`gitlab.test.local:5050`).

![Pipeline הצלחה](screenshots/06-pipeline-success.png)

---

### 6.5 Deployment ב-K3s — 3 רפליקות

### מה להראות בצילום מסך

| # | קובץ מוצע | תוכן הצילום |
|---|-----------|-------------|
| 6.5a | `screenshots/06-kubectl-deployment.png` | `kubectl get deployment word` — **3** רפליקות רצות |
| 6.5b | `screenshots/06-kubectl-pods.png` | `kubectl get pods -l app=word` — שלושה Pods **Running** |
| 6.5c | `screenshots/06-kubectl-service.png` | `kubectl get svc word` — **NodePort 30500** |
| 6.5d | `screenshots/06-curl-nodeport.png` | `curl -s http://k3s.test.local:30500/` — JSON עם אותה `word` (load balancer של השירות מפנה לאחד הפודים) |

### הסבר קצר

הוגדר **Deployment** בשם `word` עם **replicas: 3**. ה-Pods משתמשים בתמונה מרג'יסטרי GitLab. **Service** מסוג **NodePort** חושף את השירות על פורט **30500** בצומת, כך שניתן לבדוק מכל לקוח ברשת עם `http://k3s.test.local:30500/`.

![שלוש רפליקות](screenshots/06-kubectl-pods.png)

---

## נספח — פקודות לאימות מהיר (ללא צילום)

ניתן להדביק פלט טרמינל במקום חלק מהצילומים, אם המדריך מאשר:

```bash
# DNS
dig @10.20.30.250 gitlab.test.local +short
dig @10.20.30.250 -x 10.20.30.100 +short

# NAT (ממכונה פרטית)
ping -c 2 8.8.8.8

# GitLab
curl -sI http://gitlab.test.local/users/sign_in | head -1

# אפליקציה
curl -s http://k3s.test.local:30500/
```

---

## סיכום

| נושא | בוצע (סמן) |
|------|------------|
| VMs Ubuntu 22.04, רשת פרטית + נתב דו-ממשקי | ☐ |
| NAT ו-forwarding | ☐ |
| BIND — קדימה ואחורה ל-test.local | ☐ |
| GitLab CE, developer, Runner, Registry | ☐ |
| Workstation: Docker, Git, developer, SSH→GitLab | ☐ |
| K3s single node | ☐ |
| פרויקט word, Flask, Dockerfile, CI, 3 replicas | ☐ |

בהצלחה בהגשה.
