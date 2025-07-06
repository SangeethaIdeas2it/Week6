using Microsoft.EntityFrameworkCore;
using ProductService.Infrastructure.Persistence;
using MediatR;
// using AutoMapper;
using FluentValidation;
using Serilog;

var builder = WebApplication.CreateBuilder(args);

// Serilog configuration
builder.Host.UseSerilog((ctx, lc) => lc
    .WriteTo.Console()
    .ReadFrom.Configuration(ctx.Configuration));

// Add services to the container
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));
builder.Services.AddMediatR(typeof(ProductService.Infrastructure.Products.Commands.CreateProductCommandHandler).Assembly);
builder.Services.AddAutoMapper(typeof(ProductService.Application.Products.Commands.ProductMappingProfile).Assembly);
builder.Services.AddValidatorsFromAssemblyContaining<ProductService.Application.Products.Commands.CreateProductCommand>();
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// Configure Kestrel to listen on port 8001
builder.WebHost.ConfigureKestrel(options =>
{
    options.ListenAnyIP(8001);
});

var app = builder.Build();

// Configure the HTTP request pipeline
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseSerilogRequestLogging();
app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

app.Run();
