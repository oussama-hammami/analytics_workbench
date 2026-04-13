<?php
/**
 * ┌──────────────────────────────────────────────────────────────────────────┐
 * │  Analytics Workbench — Web Installer                                    │
 * │  Version 1.0.0  ·  Compatible with PHP 7.4+                            │
 * └──────────────────────────────────────────────────────────────────────────┘
 */

declare(strict_types=1);
session_start();

// ─── AJAX early-exit (must run before any output) ────────────────────────────
if (isset($_GET['ajax']) && $_GET['ajax'] === 'test_db' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    // Forward declaration — function defined further down; require it inline.
    $db = [
        'host'   => trim($_POST['db_host']   ?? 'localhost'),
        'port'   => trim($_POST['db_port']   ?? '3306'),
        'name'   => trim($_POST['db_name']   ?? ''),
        'user'   => trim($_POST['db_user']   ?? ''),
        'pass'   => (string)($_POST['db_pass'] ?? ''),
        'prefix' => 'aw_',
    ];
    try {
        $dsn = "mysql:host={$db['host']};port={$db['port']};dbname={$db['name']};charset=utf8mb4";
        new PDO($dsn, $db['user'], $db['pass'], [PDO::ATTR_TIMEOUT => 5, PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
        header('Content-Type: application/json');
        echo json_encode(['ok' => true, 'msg' => 'Connected successfully']);
    } catch (\PDOException $e) {
        header('Content-Type: application/json');
        echo json_encode(['ok' => false, 'msg' => $e->getMessage()]);
    }
    exit;
}

// ─── Constants ────────────────────────────────────────────────────────────────
define('INSTALLER_VER', '1.0.0');
define('APP_ROOT',      realpath(dirname(__DIR__)));
define('LOCK_FILE',     APP_ROOT . DIRECTORY_SEPARATOR . '.installed');
define('ENV_FILE',      APP_ROOT . DIRECTORY_SEPARATOR . 'app.env');
define('MIN_PHP',       '7.4.0');
define('MIN_PYTHON',    '3.8');
define('TOTAL_STEPS',   4);

// ─── Already-installed guard ──────────────────────────────────────────────────
if (file_exists(LOCK_FILE)) {
    render_locked();
    exit;
}

// ─── Session init ─────────────────────────────────────────────────────────────
if (!isset($_SESSION['install_step'])) {
    $_SESSION['install_step'] = 1;
}

$step   = (int) ($_SESSION['install_step'] ?? 1);
$errors = [];
$info   = [];

// ─── POST handler ─────────────────────────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = trim($_POST['action'] ?? '');

    // ── Step 1 → 2: requirements passed ──────────────────────────────────────
    if ($action === 'next_step1') {
        $checks   = get_requirements();
        $allPass  = array_reduce(
            $checks,
            fn($carry, $c) => $carry && (!$c['required'] || $c['pass']),
            true
        );
        if ($allPass) {
            $_SESSION['install_step'] = 2;
            $step = 2;
        } else {
            $errors[] = 'One or more required checks failed. Please resolve them before continuing.';
        }
    }

    // ── Step 2 → 3: database setup ────────────────────────────────────────────
    if ($action === 'save_db') {
        $db = [
            'host'   => trim($_POST['db_host']   ?? 'localhost'),
            'port'   => trim($_POST['db_port']   ?? '3306'),
            'name'   => trim($_POST['db_name']   ?? ''),
            'user'   => trim($_POST['db_user']   ?? ''),
            'pass'   => (string) ($_POST['db_pass'] ?? ''),
            'prefix' => preg_replace('/[^a-z0-9_]/i', '', trim($_POST['db_prefix'] ?? 'aw_')),
        ];

        if ($db['name'] === '') $errors[] = 'Database name is required.';
        if ($db['user'] === '') $errors[] = 'Database username is required.';

        if (empty($errors)) {
            [$ok, $msg] = test_db_connection($db);
            if (!$ok) {
                $errors[] = "Connection failed: $msg";
            } else {
                [$mok, $mmsg] = run_migrations($db);
                if (!$mok) {
                    $errors[] = "Migration error: $mmsg";
                } else {
                    $_SESSION['db_config']    = $db;
                    $_SESSION['install_step'] = 3;
                    $step = 3;
                    $info[] = 'Database connected and schema applied successfully.';
                }
            }
        }
    }

    // ── Step 3 → 4: admin account + .env write ────────────────────────────────
    if ($action === 'create_admin') {
        $admin = [
            'name'  => trim($_POST['admin_name']  ?? ''),
            'email' => trim($_POST['admin_email'] ?? ''),
            'pass'  => (string) ($_POST['admin_pass']  ?? ''),
            'pass2' => (string) ($_POST['admin_pass2'] ?? ''),
        ];
        $app = [
            'name' => trim($_POST['app_name'] ?? 'Analytics Workbench'),
            'url'  => rtrim(trim($_POST['app_url'] ?? ''), '/'),
            'port' => trim($_POST['app_port'] ?? '8501'),
        ];

        if ($admin['name'] === '')  $errors[] = 'Full name is required.';
        if (!filter_var($admin['email'], FILTER_VALIDATE_EMAIL)) $errors[] = 'A valid email address is required.';
        if (strlen($admin['pass']) < 8)  $errors[] = 'Password must be at least 8 characters.';
        if ($admin['pass'] !== $admin['pass2'])  $errors[] = 'Passwords do not match.';
        if ($app['url'] === '')  $errors[] = 'Application URL is required.';

        if (empty($errors)) {
            $db = $_SESSION['db_config'] ?? [];

            [$aok, $amsg] = insert_superadmin($db, $admin);
            if (!$aok) {
                $errors[] = "Could not create admin account: $amsg";
            } else {
                [$eok, $emsg] = write_env_file($db, $admin, $app);
                if (!$eok) {
                    $errors[] = "Could not write .env file: $emsg";
                } else {
                    // Write lock file
                    file_put_contents(LOCK_FILE, date('Y-m-d H:i:s') . "\n");
                    $_SESSION['admin_email']  = $admin['email'];
                    $_SESSION['app_url']      = $app['url'];
                    $_SESSION['app_port']     = $app['port'];
                    $_SESSION['install_step'] = 4;
                    $step = 4;
                }
            }
        }
    }
}

// ─── Helper: refresh step from session ───────────────────────────────────────
$step = (int) ($_SESSION['install_step'] ?? 1);

// ═════════════════════════════════════════════════════════════════════════════
//  LOGIC FUNCTIONS
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Return a list of requirement checks.
 * Each entry: ['label', 'pass' (bool), 'value' (string), 'required' (bool)]
 */
function get_requirements(): array {
    $r = [];

    // PHP version
    $r[] = [
        'label'    => 'PHP Version ≥ ' . MIN_PHP,
        'pass'     => version_compare(PHP_VERSION, MIN_PHP, '>='),
        'value'    => PHP_VERSION,
        'required' => true,
        'group'    => 'PHP',
    ];

    // Required PHP extensions
    foreach (['pdo' => 'PDO', 'pdo_mysql' => 'PDO MySQL', 'mbstring' => 'mbstring', 'openssl' => 'OpenSSL', 'json' => 'JSON'] as $ext => $label) {
        $loaded = extension_loaded($ext);
        $r[] = [
            'label'    => "PHP Extension: $label",
            'pass'     => $loaded,
            'value'    => $loaded ? 'Enabled' : 'Missing',
            'required' => true,
            'group'    => 'PHP',
        ];
    }

    // Optional extensions
    foreach (['curl' => 'cURL', 'zip' => 'ZIP'] as $ext => $label) {
        $loaded = extension_loaded($ext);
        $r[] = [
            'label'    => "PHP Extension: $label",
            'pass'     => $loaded,
            'value'    => $loaded ? 'Enabled' : 'Not installed',
            'required' => false,
            'group'    => 'PHP',
        ];
    }

    // Python availability
    $pyVer = null;
    $pyBin = null;
    foreach (['python3', 'python'] as $bin) {
        $out = @shell_exec("$bin --version 2>&1");
        if ($out && preg_match('/Python\s+(\d+\.\d+\.?\d*)/', $out, $m)) {
            $pyVer = $m[1];
            $pyBin = $bin;
            break;
        }
    }
    $pyOk = $pyVer !== null && version_compare($pyVer, MIN_PYTHON, '>=');
    $r[] = [
        'label'    => 'Python ≥ ' . MIN_PYTHON,
        'pass'     => $pyOk,
        'value'    => $pyVer ? "Python {$pyVer} ({$pyBin})" : 'Not found in PATH',
        'required' => true,
        'group'    => 'Runtime',
    ];

    // pip
    $pipOut = trim((string)(@shell_exec('pip3 --version 2>&1') ?? @shell_exec('pip --version 2>&1') ?? ''));
    $pipOk  = str_contains($pipOut, 'pip');
    $r[] = [
        'label'    => 'pip (Python package manager)',
        'pass'     => $pipOk,
        'value'    => $pipOk ? explode(' ', $pipOut)[0] . ' ' . (explode(' ', $pipOut)[1] ?? '') : 'Not found',
        'required' => false,
        'group'    => 'Runtime',
    ];

    // Filesystem permissions
    $paths = [
        APP_ROOT                             => ['App Root Directory',    true],
        APP_ROOT . '/session_data'           => ['session_data/',         false],
    ];
    foreach ($paths as $path => [$label, $req]) {
        $exists   = file_exists($path);
        $writable = $exists && is_writable($path);
        $r[] = [
            'label'    => "$label — Writable",
            'pass'     => $writable,
            'value'    => !$exists ? 'Not found' : ($writable ? 'Writable' : 'Read-only'),
            'required' => $req,
            'group'    => 'Permissions',
        ];
    }

    // .env writable
    $envOk = file_exists(ENV_FILE) ? is_writable(ENV_FILE) : is_writable(APP_ROOT);
    $r[] = [
        'label'    => '.env File — Writable',
        'pass'     => $envOk,
        'value'    => $envOk ? 'OK' : 'Cannot write',
        'required' => true,
        'group'    => 'Permissions',
    ];

    return $r;
}

/** Test a PDO MySQL connection. Returns [bool $ok, string $message]. */
function test_db_connection(array $db): array {
    try {
        $dsn = "mysql:host={$db['host']};port={$db['port']};dbname={$db['name']};charset=utf8mb4";
        new PDO($dsn, $db['user'], $db['pass'], [
            PDO::ATTR_TIMEOUT      => 5,
            PDO::ATTR_ERRMODE      => PDO::ERRMODE_EXCEPTION,
        ]);
        return [true, 'Connected'];
    } catch (\PDOException $e) {
        return [false, $e->getMessage()];
    }
}

/** Run DDL migrations. Returns [bool $ok, string $message]. */
function run_migrations(array $db): array {
    try {
        $dsn = "mysql:host={$db['host']};port={$db['port']};dbname={$db['name']};charset=utf8mb4";
        $pdo = new PDO($dsn, $db['user'], $db['pass'], [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
        $p   = $db['prefix'];

        $stmts = [
            // Users table
            "CREATE TABLE IF NOT EXISTS `{$p}users` (
                `id`         INT UNSIGNED NOT NULL AUTO_INCREMENT,
                `name`       VARCHAR(100)  NOT NULL,
                `email`      VARCHAR(150)  NOT NULL,
                `password`   VARCHAR(255)  NOT NULL,
                `role`       ENUM('superadmin','admin','viewer') NOT NULL DEFAULT 'viewer',
                `is_active`  TINYINT(1)   NOT NULL DEFAULT 1,
                `last_login` TIMESTAMP    NULL,
                `created_at` TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `updated_at` TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                UNIQUE KEY `uq_email` (`email`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",

            // Settings table
            "CREATE TABLE IF NOT EXISTS `{$p}settings` (
                `id`            INT UNSIGNED NOT NULL AUTO_INCREMENT,
                `setting_key`   VARCHAR(100) NOT NULL,
                `setting_value` LONGTEXT,
                `autoload`      TINYINT(1)   NOT NULL DEFAULT 1,
                `created_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `updated_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                UNIQUE KEY `uq_key` (`setting_key`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",

            // Seed default settings
            "INSERT IGNORE INTO `{$p}settings` (`setting_key`, `setting_value`, `autoload`) VALUES
                ('app_version', '1.0.0', 1),
                ('install_date', NOW(), 1),
                ('max_upload_mb', '50', 1),
                ('allow_registration', '0', 1)",
        ];

        foreach ($stmts as $stmt) {
            $pdo->exec($stmt);
        }

        return [true, 'Migrations applied'];
    } catch (\PDOException $e) {
        return [false, $e->getMessage()];
    }
}

/** Insert the super-admin user. Returns [bool $ok, string $message]. */
function insert_superadmin(array $db, array $admin): array {
    try {
        $dsn  = "mysql:host={$db['host']};port={$db['port']};dbname={$db['name']};charset=utf8mb4";
        $pdo  = new PDO($dsn, $db['user'], $db['pass'], [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
        $p    = $db['prefix'];
        $hash = password_hash($admin['pass'], PASSWORD_BCRYPT, ['cost' => 12]);

        $stmt = $pdo->prepare(
            "INSERT INTO `{$p}users` (`name`, `email`, `password`, `role`)
             VALUES (:name, :email, :password, 'superadmin')"
        );
        $stmt->execute([
            ':name'     => $admin['name'],
            ':email'    => $admin['email'],
            ':password' => $hash,
        ]);

        // Seed app_name into settings
        $pdo->prepare(
            "INSERT IGNORE INTO `{$p}settings` (`setting_key`, `setting_value`) VALUES ('admin_email', :email)"
        )->execute([':email' => $admin['email']]);

        return [true, 'Admin created'];
    } catch (\PDOException $e) {
        return [false, $e->getMessage()];
    }
}

/** Write the .env file. Returns [bool $ok, string $message]. */
function write_env_file(array $db, array $admin, array $app): array {
    $secret = bin2hex(random_bytes(32));
    $lines  = [
        '# ──────────────────────────────────────────────────────────────────',
        '# Analytics Workbench — Environment Configuration',
        '# Generated by the Web Installer on ' . date('Y-m-d H:i:s'),
        '# Keep this file secret. Do NOT commit it to version control.',
        '# ──────────────────────────────────────────────────────────────────',
        '',
        '# Application',
        'APP_NAME="' . addslashes($app['name']) . '"',
        'APP_ENV=production',
        'APP_DEBUG=false',
        'APP_URL=' . $app['url'],
        'APP_SECRET_KEY=' . $secret,
        '',
        '# Database',
        'DB_CONNECTION=mysql',
        'DB_HOST='     . $db['host'],
        'DB_PORT='     . $db['port'],
        'DB_DATABASE=' . $db['name'],
        'DB_USERNAME=' . $db['user'],
        'DB_PASSWORD=' . $db['pass'],
        'DB_PREFIX='   . $db['prefix'],
        '',
        '# Streamlit Server',
        'STREAMLIT_SERVER_PORT='       . $app['port'],
        'STREAMLIT_SERVER_ADDRESS=0.0.0.0',
        'STREAMLIT_SERVER_HEADLESS=true',
        'STREAMLIT_BROWSER_GATHER_USAGE_STATS=false',
        '',
        '# Super Admin (reference — auth is database-backed)',
        'ADMIN_EMAIL=' . $admin['email'],
    ];

    $content = implode("\n", $lines) . "\n";
    $written = file_put_contents(ENV_FILE, $content);
    return $written !== false
        ? [true,  'Written to ' . ENV_FILE]
        : [false, 'Could not write to ' . ENV_FILE . ' — check permissions.'];
}

/** HTML-escape a value. */
function h(string $s): string {
    return htmlspecialchars($s, ENT_QUOTES | ENT_HTML5, 'UTF-8');
}

// ═════════════════════════════════════════════════════════════════════════════
//  RENDER: LOCKED PAGE
// ═════════════════════════════════════════════════════════════════════════════
function render_locked(): void { ?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Already Installed — Analytics Workbench</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex items-center justify-center">
  <div class="text-center max-w-md px-6">
    <div class="w-16 h-16 bg-amber-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
      <svg class="w-8 h-8 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
      </svg>
    </div>
    <h1 class="text-xl font-semibold mb-2 text-amber-300">Already Installed</h1>
    <p class="text-slate-400 text-sm mb-6">Analytics Workbench has already been installed on this server. For security, please <strong class="text-slate-200">delete the <code>install/</code> directory</strong>.</p>
    <p class="text-xs text-slate-600">If you need to re-install, remove the <code>.installed</code> file from the app root.</p>
  </div>
</body>
</html>
<?php }

// ═════════════════════════════════════════════════════════════════════════════
//  RENDER: MAIN PAGE
// ═════════════════════════════════════════════════════════════════════════════

$stepLabels = [1 => 'Requirements', 2 => 'Database', 3 => 'Admin Account', 4 => 'Complete'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Installation Wizard — Analytics Workbench</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', ui-sans-serif, system-ui, sans-serif; }
    .step-connector { transition: background 0.4s ease; }
    input:focus { outline: none; box-shadow: 0 0 0 2px rgba(99,102,241,0.5); }
    .badge-pass  { background: rgba(34,197,94,.15);  color: #4ade80; }
    .badge-fail  { background: rgba(239,68,68,.15);  color: #f87171; }
    .badge-warn  { background: rgba(234,179,8,.15);  color: #facc15; }
    @keyframes fadeUp { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
    .fade-up { animation: fadeUp .35s ease both; }
    @keyframes spin { to { transform:rotate(360deg); } }
    .spinner { animation: spin 1s linear infinite; }
  </style>
</head>

<body class="bg-slate-950 text-slate-100 min-h-screen">

  <!-- ── Header ─────────────────────────────────────────────────────────── -->
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
    <div class="max-w-2xl mx-auto px-6 py-4 flex items-center gap-3">
      <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-900/40">
        <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
      </div>
      <div>
        <p class="text-sm font-semibold leading-none text-slate-100">Analytics Workbench</p>
        <p class="text-xs text-slate-500 mt-0.5">Installation Wizard · v<?= INSTALLER_VER ?></p>
      </div>
    </div>
  </header>

  <!-- ── Step Indicator ─────────────────────────────────────────────────── -->
  <div class="max-w-2xl mx-auto px-6 pt-8 pb-2">
    <div class="flex items-center">
      <?php foreach ($stepLabels as $n => $label):
        $isActive   = $n === $step;
        $isDone     = $n < $step;
        $isLast     = $n === TOTAL_STEPS;
        $circleBase = 'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 z-10 transition-all duration-300';
        if ($isDone)       $circle = "$circleBase bg-indigo-600 text-white shadow-lg shadow-indigo-900/50";
        elseif ($isActive) $circle = "$circleBase bg-indigo-500 text-white ring-4 ring-indigo-900 shadow-lg";
        else               $circle = "$circleBase bg-slate-800 text-slate-500";
        $labelClass = $isActive ? 'text-indigo-400 font-semibold' : ($isDone ? 'text-slate-400' : 'text-slate-600');
      ?>
        <div class="flex flex-col items-center gap-1.5">
          <div class="<?= $circle ?>">
            <?php if ($isDone): ?>
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
            <?php else: ?>
              <?= $n ?>
            <?php endif; ?>
          </div>
          <span class="text-[10px] <?= $labelClass ?> hidden sm:block whitespace-nowrap"><?= h($label) ?></span>
        </div>
        <?php if (!$isLast): ?>
          <div class="flex-1 h-px mx-1 step-connector <?= $n < $step ? 'bg-indigo-600' : 'bg-slate-800' ?>"></div>
        <?php endif; ?>
      <?php endforeach; ?>
    </div>
  </div>

  <!-- ── Main Content ───────────────────────────────────────────────────── -->
  <main class="max-w-2xl mx-auto px-6 py-8">

    <?php // ── Error / Info alerts ───────────────────────────────────────── ?>
    <?php if (!empty($errors)): ?>
      <div class="mb-5 rounded-xl bg-red-950/50 border border-red-900/60 p-4 fade-up">
        <div class="flex gap-3">
          <svg class="w-5 h-5 text-red-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div>
            <?php foreach ($errors as $e): ?>
              <p class="text-sm text-red-300"><?= h($e) ?></p>
            <?php endforeach; ?>
          </div>
        </div>
      </div>
    <?php endif; ?>

    <?php if (!empty($info)): ?>
      <div class="mb-5 rounded-xl bg-emerald-950/50 border border-emerald-900/60 p-4 fade-up">
        <?php foreach ($info as $i): ?>
          <p class="text-sm text-emerald-300"><?= h($i) ?></p>
        <?php endforeach; ?>
      </div>
    <?php endif; ?>

    <!-- ════════════════════════════════════════════════════════════════════ -->
    <!--  STEP 1 — Welcome & Requirements                                   -->
    <!-- ════════════════════════════════════════════════════════════════════ -->
    <?php if ($step === 1):
      $checks = get_requirements();
      $groups = array_unique(array_column($checks, 'group'));
    ?>
    <div class="fade-up">
      <div class="mb-6">
        <h2 class="text-xl font-semibold text-slate-100">Welcome to Analytics Workbench</h2>
        <p class="text-slate-400 text-sm mt-1">Before we begin, let's make sure your server meets all requirements.</p>
      </div>

      <?php foreach ($groups as $group):
        $groupChecks = array_filter($checks, fn($c) => $c['group'] === $group);
      ?>
        <div class="mb-4 rounded-xl bg-slate-900 border border-slate-800 overflow-hidden">
          <div class="px-4 py-2.5 bg-slate-800/60 border-b border-slate-800">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400"><?= h($group) ?></span>
          </div>
          <div class="divide-y divide-slate-800/50">
            <?php foreach ($groupChecks as $c):
              $badgeClass = $c['pass'] ? 'badge-pass' : ($c['required'] ? 'badge-fail' : 'badge-warn');
              $badgeText  = $c['pass'] ? 'Pass' : ($c['required'] ? 'Fail' : 'Optional');
              $iconPath   = $c['pass']
                ? 'M5 13l4 4L19 7'
                : 'M6 18L18 6M6 6l12 12';
              $iconColor  = $c['pass'] ? 'text-emerald-400' : ($c['required'] ? 'text-red-400' : 'text-amber-400');
            ?>
              <div class="flex items-center gap-3 px-4 py-3">
                <svg class="w-4 h-4 <?= $iconColor ?> shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="<?= $iconPath ?>"/>
                </svg>
                <span class="flex-1 text-sm text-slate-300"><?= h($c['label']) ?></span>
                <span class="text-xs text-slate-500 mr-2"><?= h($c['value']) ?></span>
                <span class="text-xs font-medium px-2 py-0.5 rounded-full <?= $badgeClass ?>"><?= $badgeText ?></span>
              </div>
            <?php endforeach; ?>
          </div>
        </div>
      <?php endforeach; ?>

      <form method="POST" class="mt-6 flex justify-end">
        <input type="hidden" name="action" value="next_step1">
        <button type="submit"
          class="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl transition-colors">
          Continue to Database Setup
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
          </svg>
        </button>
      </form>
    </div>

    <!-- ════════════════════════════════════════════════════════════════════ -->
    <!--  STEP 2 — Database Configuration                                   -->
    <!-- ════════════════════════════════════════════════════════════════════ -->
    <?php elseif ($step === 2): ?>
    <div class="fade-up">
      <div class="mb-6">
        <h2 class="text-xl font-semibold text-slate-100">Database Configuration</h2>
        <p class="text-slate-400 text-sm mt-1">Enter your MySQL credentials. The installer will test the connection and apply the schema.</p>
      </div>

      <form method="POST" id="dbForm">
        <input type="hidden" name="action" value="save_db">

        <div class="rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-5">

          <div class="grid grid-cols-3 gap-4">
            <div class="col-span-2">
              <label class="block text-xs font-medium text-slate-400 mb-1.5">Database Host</label>
              <input type="text" name="db_host" value="<?= h($_POST['db_host'] ?? 'localhost') ?>"
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors"
                placeholder="localhost" required>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-400 mb-1.5">Port</label>
              <input type="number" name="db_port" value="<?= h($_POST['db_port'] ?? '3306') ?>"
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors"
                placeholder="3306">
            </div>
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Database Name</label>
            <input type="text" name="db_name" value="<?= h($_POST['db_name'] ?? '') ?>"
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors"
              placeholder="analytics_workbench" required>
            <p class="text-xs text-slate-600 mt-1">The database must already exist on your server.</p>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-slate-400 mb-1.5">Username</label>
              <input type="text" name="db_user" value="<?= h($_POST['db_user'] ?? '') ?>"
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors"
                placeholder="root" required autocomplete="off">
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-400 mb-1.5">Password</label>
              <input type="password" name="db_pass" value=""
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors"
                placeholder="••••••••" autocomplete="new-password">
            </div>
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Table Prefix</label>
            <input type="text" name="db_prefix" value="<?= h($_POST['db_prefix'] ?? 'aw_') ?>"
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors"
              placeholder="aw_">
            <p class="text-xs text-slate-600 mt-1">Tables will be created as <code class="text-slate-500">aw_users</code>, <code class="text-slate-500">aw_settings</code>, etc.</p>
          </div>
        </div>

        <!-- Tables that will be created -->
        <div class="mt-4 rounded-xl bg-slate-900/50 border border-slate-800/60 px-4 py-3">
          <p class="text-xs font-medium text-slate-500 mb-2">Tables that will be created</p>
          <div class="flex flex-wrap gap-2">
            <?php foreach (['users', 'settings'] as $t): ?>
              <span class="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 font-mono"><?= h(($_POST['db_prefix'] ?? 'aw_') . $t) ?></span>
            <?php endforeach; ?>
          </div>
        </div>

        <div class="mt-6 flex items-center justify-between">
          <button type="button" onclick="testConnection()"
            class="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-xl transition-colors border border-slate-700">
            <svg id="testIcon" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
            Test Connection
          </button>
          <span id="testResult" class="text-xs text-slate-500"></span>
          <button type="submit" id="submitBtn"
            class="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl transition-colors">
            Apply & Continue
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
            </svg>
          </button>
        </div>
      </form>
    </div>

    <script>
    async function testConnection() {
      const form   = document.getElementById('dbForm');
      const icon   = document.getElementById('testIcon');
      const result = document.getElementById('testResult');
      const data   = new FormData(form);
      data.set('action', 'test_connection_ajax');

      icon.classList.add('spinner');
      result.textContent = 'Testing…';
      result.className   = 'text-xs text-slate-400';

      const resp = await fetch('?ajax=test_db', {
        method: 'POST', body: data
      });
      const json = await resp.json();
      icon.classList.remove('spinner');

      if (json.ok) {
        result.textContent = '✓ Connection successful';
        result.className   = 'text-xs text-emerald-400 font-medium';
      } else {
        result.textContent = '✗ ' + json.msg;
        result.className   = 'text-xs text-red-400';
      }
    }
    </script>

    <!-- ════════════════════════════════════════════════════════════════════ -->
    <!--  STEP 3 — Super Admin Account                                      -->
    <!-- ════════════════════════════════════════════════════════════════════ -->
    <?php elseif ($step === 3): ?>
    <div class="fade-up">
      <div class="mb-6">
        <h2 class="text-xl font-semibold text-slate-100">Administrator Account</h2>
        <p class="text-slate-400 text-sm mt-1">Create the super-admin account and finalise your application settings.</p>
      </div>

      <form method="POST">
        <input type="hidden" name="action" value="create_admin">

        <!-- App Settings -->
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-5 mb-4">
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Application Settings</p>

          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Application Name</label>
            <input type="text" name="app_name" value="<?= h($_POST['app_name'] ?? 'Analytics Workbench') ?>"
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors">
          </div>

          <div class="grid grid-cols-3 gap-4">
            <div class="col-span-2">
              <label class="block text-xs font-medium text-slate-400 mb-1.5">Application URL</label>
              <input type="url" name="app_url" value="<?= h($_POST['app_url'] ?? (isset($_SERVER['HTTPS']) ? 'https' : 'http') . '://' . ($_SERVER['HTTP_HOST'] ?? 'localhost')) ?>"
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors"
                placeholder="https://example.com" required>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-400 mb-1.5">Streamlit Port</label>
              <input type="number" name="app_port" value="<?= h($_POST['app_port'] ?? '8501') ?>"
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors"
                placeholder="8501">
            </div>
          </div>
        </div>

        <!-- Admin Account -->
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-5">
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Super Admin Account</p>

          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Full Name</label>
            <input type="text" name="admin_name" value="<?= h($_POST['admin_name'] ?? '') ?>"
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors"
              placeholder="John Doe" required autocomplete="name">
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Email Address</label>
            <input type="email" name="admin_email" value="<?= h($_POST['admin_email'] ?? '') ?>"
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors"
              placeholder="admin@example.com" required autocomplete="email">
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-slate-400 mb-1.5">Password</label>
              <input type="password" name="admin_pass" id="adminPass"
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors"
                placeholder="Min. 8 characters" required autocomplete="new-password" minlength="8">
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-400 mb-1.5">Confirm Password</label>
              <input type="password" name="admin_pass2" id="adminPass2"
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-indigo-500 transition-colors"
                placeholder="Repeat password" required autocomplete="new-password">
            </div>
          </div>

          <!-- Password strength indicator -->
          <div>
            <div class="flex gap-1 h-1 rounded-full overflow-hidden" id="strengthBar">
              <div class="flex-1 bg-slate-800 rounded-full" id="sb1"></div>
              <div class="flex-1 bg-slate-800 rounded-full" id="sb2"></div>
              <div class="flex-1 bg-slate-800 rounded-full" id="sb3"></div>
              <div class="flex-1 bg-slate-800 rounded-full" id="sb4"></div>
            </div>
            <p class="text-xs text-slate-600 mt-1" id="strengthLabel">Enter a password</p>
          </div>
        </div>

        <div class="mt-6 flex justify-end">
          <button type="submit"
            class="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl transition-colors">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
            </svg>
            Complete Installation
          </button>
        </div>
      </form>
    </div>

    <script>
    (function () {
      const p1 = document.getElementById('adminPass');
      const p2 = document.getElementById('adminPass2');
      const bars = [document.getElementById('sb1'), document.getElementById('sb2'),
                    document.getElementById('sb3'), document.getElementById('sb4')];
      const label = document.getElementById('strengthLabel');
      const colors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-emerald-500'];
      const labels = ['Weak', 'Fair', 'Good', 'Strong'];

      p1.addEventListener('input', () => {
        const v   = p1.value;
        let score = 0;
        if (v.length >= 8)  score++;
        if (/[A-Z]/.test(v)) score++;
        if (/[0-9]/.test(v)) score++;
        if (/[^A-Za-z0-9]/.test(v)) score++;
        bars.forEach((b, i) => {
          b.className = 'flex-1 rounded-full transition-colors ' +
            (i < score ? colors[score - 1] : 'bg-slate-800');
        });
        label.textContent = v.length === 0 ? 'Enter a password' : labels[score - 1] || 'Too short';
      });

      p2.addEventListener('input', () => {
        p2.style.borderColor = p2.value === p1.value ? '#10b981' : '#ef4444';
      });
    })();
    </script>

    <!-- ════════════════════════════════════════════════════════════════════ -->
    <!--  STEP 4 — Complete                                                 -->
    <!-- ════════════════════════════════════════════════════════════════════ -->
    <?php elseif ($step === 4):
      $appUrl  = h($_SESSION['app_url']  ?? '');
      $appPort = h($_SESSION['app_port'] ?? '8501');
      $adminEM = h($_SESSION['admin_email'] ?? '');
    ?>
    <div class="fade-up text-center">
      <!-- Success icon -->
      <div class="w-20 h-20 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center mx-auto mb-5 mt-2">
        <svg class="w-10 h-10 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
        </svg>
      </div>

      <h2 class="text-2xl font-bold text-slate-100 mb-2">Installation Complete!</h2>
      <p class="text-slate-400 text-sm mb-8 max-w-md mx-auto">Analytics Workbench has been successfully installed. Start the Streamlit server and log in with your admin account.</p>

      <!-- Summary cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8 text-left">
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
          <p class="text-xs text-slate-500 mb-1">Admin Email</p>
          <p class="text-sm font-medium text-slate-200 truncate"><?= $adminEM ?></p>
        </div>
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
          <p class="text-xs text-slate-500 mb-1">App URL</p>
          <p class="text-sm font-medium text-indigo-400 truncate"><?= $appUrl ?>:<?= $appPort ?></p>
        </div>
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
          <p class="text-xs text-slate-500 mb-1">.env File</p>
          <p class="text-sm font-medium text-emerald-400">Written successfully</p>
        </div>
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
          <p class="text-xs text-slate-500 mb-1">Database</p>
          <p class="text-sm font-medium text-emerald-400">Schema applied</p>
        </div>
      </div>

      <!-- Next steps -->
      <div class="rounded-xl bg-slate-900 border border-amber-900/40 p-5 text-left mb-6">
        <p class="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-3">Next Steps</p>
        <ol class="space-y-2.5 text-sm text-slate-400">
          <li class="flex gap-3">
            <span class="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">1</span>
            <span><strong class="text-slate-200">Delete the <code>install/</code> directory</strong> from your server immediately to prevent re-installation.</span>
          </li>
          <li class="flex gap-3">
            <span class="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">2</span>
            <span>Install Python dependencies: <code class="bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">pip install -r requirements.txt</code></span>
          </li>
          <li class="flex gap-3">
            <span class="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">3</span>
            <span>Start the app: <code class="bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">streamlit run app.py</code></span>
          </li>
          <li class="flex gap-3">
            <span class="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">4</span>
            <span>Open <a href="<?= $appUrl ?>:<?= $appPort ?>" target="_blank" class="text-indigo-400 underline underline-offset-2"><?= $appUrl ?>:<?= $appPort ?></a> in your browser.</span>
          </li>
        </ol>
      </div>

      <a href="<?= $appUrl ?>:<?= $appPort ?>" target="_blank"
        class="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl transition-colors text-sm">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
        </svg>
        Open Analytics Workbench
      </a>
    </div>
    <?php endif; ?>

  </main>

  <!-- ── Footer ─────────────────────────────────────────────────────────── -->
  <footer class="border-t border-slate-900 mt-8">
    <div class="max-w-2xl mx-auto px-6 py-4 flex items-center justify-between">
      <p class="text-xs text-slate-700">Analytics Workbench v<?= INSTALLER_VER ?></p>
      <p class="text-xs text-slate-700">Step <?= $step ?> of <?= TOTAL_STEPS ?></p>
    </div>
  </footer>

</body>
</html>
