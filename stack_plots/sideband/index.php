<!DOCTYPE html>
<html>
<head>
<title><?php echo getcwd(); ?></title>
<style type='text/css'>
body {
    font-family: "Corbel", sans-serif;
    font-size: 9pt;
    line-height: 10.5pt;
}

ul.subdirs {
    padding: 0pt;
}
li.subdirs {
    display: inline;
    list-style-type: none;
    padding-right: 20px;
}

div.pic h3 {
    font-size: 11pt;
    margin: 0.5em 1em 0.2em 1em;
}
div.pic p {
    font-size: 11pt;
    margin: 0.2em 1em 0.1em 1em;
}
div.pic {
    display: block;
    float: left;
    background-color: white;
    border: 1px solid #ccc;
    padding: 2px;
    text-align: center;
    margin: 2px 10px 10px 2px;
}
a { text-decoration: none; color: rgb(0,0,80); }
a:hover { text-decoration: underline; color: rgb(255,80,80); }
table {
    width: 100%;
    border-collapse: collapse;
}
th, td {
    border: 1px solid #ccc;
    padding: 8px;
    text-align: left;
}
th {
    background-color: #f2f2f2;
}
tr:nth-child(odd) {
    background-color: #f9f9f9; /* light gray for odd rows */
}
</style>
</head>
<body>
<h1><?php echo getcwd(); ?></h1>
<h2>
<?php
print "<ul class='subdirs'>";
print "<li class='subdirs'>Subdirs</li>";
if (file_exists("../index.php")) {
    print "<li class='subdirs'><a href=\"../\">[..]</a></li>";
}
$subdirs = glob('*', GLOB_ONLYDIR);
if (count($subdirs) != 0 ) {
    foreach($subdirs as $dir) {
        print "<li class='subdirs'><a href=".$dir.">[".$dir."]</a></li>";
    }
}
print "</ul>";
?>
</h2>
<h2><a name="plots">Plots</a></h2>
<p><form>Filter: <input type="text" name="match" size="30" value="<?php if (isset($_GET['match'])) print htmlspecialchars($_GET['match']);  ?>" /><input type="Submit" value="Go" /></form></p>

<div>
<?php
$plotwidth = '400px';
$displayed = array();
array_push($displayed, basename($_SERVER['PHP_SELF']));
if (isset($_GET['noplots']) && $_GET['noplots']) {
    print "Plots will not be displayed.\n";
} else {
    $other_exts = array('.pdf', '.cxx', '.eps', '.root', '.txt', '.C', '.cpp');
    $filenames = glob("*.png"); sort($filenames);
    foreach ($filenames as $filename) {
        if (isset($_GET['match']) && !fnmatch('*'.$_GET['match'].'*', $filename)) continue;
        array_push($displayed, $filename);
        print "<div class='pic'>\n";
        print "<h3><a href=\"$filename\" target=\"_blank\">$filename</a></h3>";
        print "<a href=\"$filename\" target=\"_blank\"><img src=\"$filename\" style=\"border: none; width: $plotwidth; \"></a>";
        $last_modified = date("F d Y H:i:s.", filemtime($filename));
        print "<p>Last modified: $last_modified</p>";
        $others = array();
        foreach ($other_exts as $ex) {
            $other_filename = str_replace('.png', $ex, $filename);
            if (file_exists($other_filename)) {
                array_push($others, "<a class=\"file\" href=\"$other_filename\" target=\"_blank\">[" . $ex . "]</a>");
                if ($ex != '.txt') array_push($displayed, $other_filename);
            }
        }
        if ($others) print "<p>Also as ".implode(', ', $others)."</p>";
        print "</div>";
    }
}
?>
</div>
<div style="display: block; clear:both;">
<h2><a name="files">Files</a></h2>
<form method="post">
<table>
    <tr>
        <th>Name</th>
        <th>Last Modified</th>
        <th>Size</th>
        <th>Remark</th>
        <th>Label Color</th>
        <th>Delete</th>
    </tr>
<?php
if (isset($_POST['delete'])) {
    $delete = $_POST['delete'];
    if (is_dir($delete)) {
        rmdir($delete);
    } else {
        unlink($delete);
    }
    header("Location: " . $_SERVER['PHP_SELF']);
    exit;
}

function cmp($a, $b) {
    return filemtime($b) - filemtime($a);
}

$file_list = array();
foreach (glob("*") as $filename) {
    if ((isset($_GET['noplots']) && $_GET['noplots']) || !in_array($filename, $displayed)) {
        if (isset($_GET['match']) && !fnmatch('*'.$_GET['match'].'*', $filename)) continue;
        $file_list[] = $filename;
    }
}

usort($file_list, "cmp");

foreach ($file_list as $filename) {
    $last_modified = date("F d Y H:i:s.", filemtime($filename));
    $size = is_dir($filename) ? '-' : filesize($filename) . ' bytes';
    $label_color = isset($_POST['label_color'][$filename]) ? htmlspecialchars($_POST['label_color'][$filename]) : '#ffffff';
    $style = "style='background-color: $label_color;'";
    if (is_dir($filename)) {
        print "<tr $style><td>[DIR] <a href=\"$filename\">$filename</a></td><td>$last_modified</td><td>$size</td><td><input type=\"text\" name=\"remark[$filename]\"></td><td><input type=\"color\" name=\"label_color[$filename]\" value=\"$label_color\"></td><td><button type=\"submit\" name=\"delete\" value=\"$filename\" onclick=\"return confirm('Are you sure you want to delete this folder?');\">Delete</button></td></tr>";
    } else {
        print "<tr $style><td><a href=\"$filename\" target=\"_blank\">$filename</a></td><td>$last_modified</td><td>$size</td><td><input type=\"text\" name=\"remark[$filename]\"></td><td><input type=\"color\" name=\"label_color[$filename]\" value=\"$label_color\"></td><td><button type=\"submit\" name=\"delete\" value=\"$filename\" onclick=\"return confirm('Are you sure you want to delete this file?');\">Delete</button></td></tr>";
    }
}
?>
</table>
<input type="submit" value="Save Labels">
</form>

<form method="post" action="">
    <input type="hidden" name="create_zip" value="1">
    <button type="submit">Download Complete Files as ZIP</button>
</form>
</div>
<div>
<h2>Legend</h2>
<ul>
    <li style="color: #ff0000;">Red - Less important/discardable</li>
    <li style="color: #00ff00;">Green - To Review</li>
    <li style="color: #0000ff;">Blue - Completed</li>
    <li style="color: #ffff00;">Yellow - In Progress</li>
    <li style="color: #ff00ff;">Magenta - Urgent</li>
    <li style="color: #00ffff;">Cyan - Low Priority</li>
    <li style="color: #ffa500;">Orange - Awaiting Feedback</li>
    <li style="color: #800080;">Purple - For Discussion</li>
    <li style="color: #808080;">Gray - Deprecated</li>
    <li style="color: #000000;">Black - Archived</li>
</ul>
</div>
</body>
</html>

<?php
if (isset($_POST['create_zip'])) {
    $zip = new ZipArchive();
    $zip_filename = 'files.zip';

    if ($zip->open($zip_filename, ZipArchive::CREATE | ZipArchive::OVERWRITE) === TRUE) {
        $files = new RecursiveIteratorIterator(
            new RecursiveDirectoryIterator('.'),
            RecursiveIteratorIterator::LEAVES_ONLY
        );

        foreach ($files as $file) {
            if (!$file->isDir()) {
                $filePath = $file->getRealPath();
                $relativePath = substr($filePath, strlen(getcwd()) + 1);
                $zip->addFile($filePath, $relativePath);
            }
        }

        $zip->close();
        header('Content-Type: application/zip');
        header('Content-Disposition: attachment; filename=' . basename($zip_filename));
        header('Content-Length: ' . filesize($zip_filename));
        readfile($zip_filename);
        unlink($zip_filename);
        exit;
    } else {
        echo 'Failed to create ZIP file.';
    }
}
?>
