const header = document.createElement('template');
header.innerHTML = `
    <div>
    <header class="header_section">
        <a href="/how" style="padding-left:5px;">
        <div class="icon_header">
            <i class='fa fa-question-circle-o'></i>
        </div>
        </a>
        <a href="/">
            <h3> besteam </h3>          
        </a> 
        <a href="mailto:manloralm@outlook.com" style="padding-right:5px;"> 
            <div class="icon_header">
                <i class='fa fa-envelope'></i>
            </div>
        </a>
    </header>
    </div>
    `
document.body.appendChild(header.content);