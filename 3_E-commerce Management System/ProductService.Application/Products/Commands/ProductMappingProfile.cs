using AutoMapper;
using ProductService.Application.Products.Commands;
using ProductService.Application.Products.Dtos;
using ProductService.Domain.Entities;

namespace ProductService.Application.Products.Commands
{
    public class ProductMappingProfile : Profile
    {
        public ProductMappingProfile()
        {
            CreateMap<CreateProductCommand, Product>();
            CreateMap<UpdateProductCommand, Product>();
            CreateMap<Product, ProductDto>();
            CreateMap<Category, CategoryDto>();
        }
    }
} 