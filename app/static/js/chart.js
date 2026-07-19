function createFakeChart(){

const canvas=document.getElementById("chart");

if(!canvas) return;

const ctx=canvas.getContext("2d");

ctx.beginPath();

ctx.moveTo(20,160);

ctx.lineTo(80,120);

ctx.lineTo(150,140);

ctx.lineTo(220,60);

ctx.lineTo(290,100);

ctx.lineWidth=4;

ctx.strokeStyle="#0d6efd";

ctx.stroke();

}
window.onload=createFakeChart;